import os
import sys
import json
import logging
import asyncio
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters
from openai import AsyncOpenAI, AsyncAzureOpenAI

# Dynamically find the project directory and add it to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))  # Current file's directory
sys.path.append(current_dir)  # Add the project root to sys.path

from security_manager import SecurityManager
from utils import generate_headers
from config import Config
from state import AgentState, init_agent_state
from cache import CACHE, SingletonTTLCache

logging.basicConfig(level=Config.LOG_LEVEL)

# Load environment variables
load_dotenv(".env")

class MCPOpenAIClient:

    def __init__(
            self,
            model: str = "gpt-4o",
            client: str = "openai",
            state: AgentState = init_agent_state(), 
            conversation_id: str = None,
            enable_cache: bool = False
        ):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
            client: The client type (openai or azure_openai).
            conversation_id: The unique identifier for each conversation
            enable_cache: whether to enable cache. If enabled, conversation_id will be used as cache key and it can't be None.
        """
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        if client == "openai":
            self.openai_client = AsyncOpenAI()
        elif client == "azure_openai" or client == "azure":
            headers = generate_headers(
                private_key_path=Config.LLM_PRIVATE_KEY_PATH,
                consumer_id=Config.CONSUMER_ID,
                env=Config.ENV,
            )
            self.openai_client = client = AsyncAzureOpenAI(
                api_key=Config.CONSUMER_ID,
                api_version=Config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                http_client = httpx.AsyncClient(verify=False, headers=headers)
            )
        else:
            raise ValueError(f"Unsupported client type: {client}")
        self.model = model
        self.state = state
        self.conversation_id = conversation_id
        if enable_cache:
            assert self.conversation_id, "conversation_id can't be None when cache is enabled"
        self.enable_cache = enable_cache

        self.security_manager = SecurityManager()
        self.history = CACHE.get(conversation_id, [])
        self.tools = None

    # abstract method to connect to the mcp server
    async def connect_to_server(self, server_uri: str):
        """Connect to an MCP server.
        Args:
            server_uri: URI of the MCP server.
        """
        # This method should be implemented in subclasses
        # to connect to the server using the appropriate transport.
        raise NotImplementedError("Subclasses should implement this method.")

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from the MCP server in OpenAI format.

        Returns:
            A list of tools in OpenAI format.
        """
        tools_result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]
    
    async def prompt(self, query: str) -> str:
        """Process a query using OpenAI and available MCP tools.

        Args:
            query: The user query.

        Returns:
            The response from OpenAI.
        """

        # Initialize message list with chat history, system prompt and latest user query
        messages = await self._get_chat_history(20)
        messages = await self._add_system_prompt(messages, Config.SYSTEM_PROMPT)
        old_message_len = len(messages)

        # Check if waiting for user approval
        if self.state["waiting_approval"]:
            if not self._approve(query):
                message = "Tool call denied by the user. What else can I do for you?"
                messages.append({"role": "assistant", "content": message})
                self.state["waiting_approval"] = False
                self.history.extend(messages[old_message_len:])
                self._update_cache(
                    CACHE,
                    {
                        self.conversation_id: self.history,
                        f"{self.conversation_id}_state": self.state,
                    }
                )
                return message
            logging.debug("")
        else:
            messages.append({"role": "user", "content": query})

        logging.info(f"chat history: {messages}")

        # Get available tools
        tools = await self._get_tools()        
        
        # Initial OpenAI API call
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        # Get assistant's response
        assistant_message = response.choices[0].message
        
        # Add assistant response
        messages.append(assistant_message)

        # Handle tool calls if present
        while assistant_message.tool_calls:
            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                # Ask for approval
                if not self.state["waiting_approval"] and self.security_manager.need_approval(tool_name):
                    self.state["waiting_approval"] = True
                    self.history.extend(messages[old_message_len:])
                    if self.enable_cache:
                        await self._update_cache(
                            CACHE,
                            {
                                self.conversation_id: self.history,
                                f"{self.conversation_id}_state": self.state
                            }
                        )
                    return f'Tool "{tool_name}" requires approval.\n Arguments: {json.dumps(args, indent=2)} \n Type "yes" or "y" to approve, anything else to deny:'

                # if await self.security_manager.check_tool_call(
                #     tool_call.function.name,
                #     json.loads(tool_call.function.arguments),
                # ):
                #     logging.info(f"Tool call {tool_call.function.name} approved.")
                # else:
                #     logging.info(f"Tool call {tool_call.function.name} denied.")
                #     messages.append({"role": "assistant", "content": f"Tool call {tool_call.function.name} denied by the user."})
                #     self.history.extend(messages[old_message_len:])
                #     return "Tool call denied by security manager."

                # Execute tool call
                result = await self.session.call_tool(
                    tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                )
                logging.debug(f"Tool call result: {result}")

                # Add tool response to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.content[0].text,
                    }
                )

            logging.info(f"Messages: {messages}")
            # Get the response from OpenAI with tool results
            assistant_message = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            assistant_message = assistant_message.choices[0].message
            messages.append(assistant_message)

        # No tool calls, return the AI message
        self.history.extend(messages[old_message_len:])
        if self.enable_cache:
            CACHE[self.conversation_id] = self.history
        return assistant_message.content

    async def _get_chat_history(self, limit: int = 20) -> list:
        """
        Get last `limit` turns of chat history
        """
        
        return self.history[-limit:]

    async def _get_tools(self) -> list[dict]:
        """
        Get available tools from MCP server
        """
        if self.tools:
            return self.tools
        
        tools = await self.get_mcp_tools()
        self.tools = tools
        return self.tools

    async def _add_system_prompt(self, messages: list, system_prompt: str) -> list:
        """
        Add system prompt to the beginning of message list if doesn't exisit
        """
        if any([m["role"] == "system" for m in messages if isinstance(m, dict)]):
            return messages
        
        messages.insert(
            0, 
            {"role": "system", "content": system_prompt}
        )
        return messages

    def _approve(self, query: str) -> bool:
        if not self.state["waiting_approval"]:
            raise ValueError("Not waiting for approval")
        
        return query.lower() == "y" or query.lower() == "yes"

    async def _update_cache(self, cache: SingletonTTLCache, pairs: dict):
        if not self.enable_cache:
            return
        
        for key, value in pairs.items():
            cache[key] = value
        return

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


class MCPOpenAIClientStdio(MCPOpenAIClient):
    """Client for interacting with OpenAI models using MCP tools."""

    def __init__(self, *args, **kwargs):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
            client: The client type (openai or azure_openai).
        """
        # Initialize session and client objects
        super().__init__(*args, **kwargs)
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

    async def connect_to_server(self, server_script_path: str = "server.py"):
        """Connect to an MCP server.

        Args:
            server_script_path: Path to the server script.
        """
        # Server configuration
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
        )

        # Connect to the server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        # Initialize the connection
        await self.session.initialize()

        # List available tools
        tools_result = await self.session.list_tools()
        logging.info("\nConnected to server with tools:")
        for tool in tools_result.tools:
            logging.info(f"  - {tool.name}: {tool.description}")


class MCPOpenAIClientSSE(MCPOpenAIClient):
    """Client for interacting with OpenAI models using MCP tools."""

    def __init__(self, *args, **kwargs):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
            client: The client type (openai or azure_openai).
        """
        # Initialize session and client objects
        super().__init__(*args, **kwargs)

    async def connect_to_server(
            self, 
            server_url: str,
            headers: Optional[Dict[str, str]] = {},
        ):
        """Connect to an MCP server using SSE.

        Args:
            server_url: URL of the SSE server.
            headers: Optional headers for the SSE connection.
        """
        # Connect to the server using SSE
        sse_transport = await self.exit_stack.enter_async_context(
            sse_client(server_url, headers=headers)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(*sse_transport)
        )

        # Initialize the connection
        await self.session.initialize()

        # List available tools
        tools_result = await self.session.list_tools()
        logging.info("\nConnected to server with tools:")
        for tool in tools_result.tools:
            logging.info(f"  - {tool.name}: {tool.description}")


async def main():
    """Main entry point for the client."""
    client = MCPOpenAIClientSSE(client="azure_openai")
    await client.connect_to_server(Config.CONFLUENCE_MCP_SERVER, headers={})

    while True:
        try:
            logging.warning("Enter your question:")
            query = input().strip().lower()
            # Example: Ask about company vacation policy
            # query = "Can you update this page https://confluence.walmart.com/pages/viewpage.action?pageId=2808261720 by changing the title to Hackathon and content to Hackathon"

            response = await client.prompt(query)
            logging.warning(f"\nResponse: {response}")

        except KeyboardInterrupt:
            break

        except Exception as e:
            logging.error(e)
            break

    await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
