import os
import sys
import json
import asyncio
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters
from openai import AsyncOpenAI


# Dynamically find the project directory and add it to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))  # Current file's directory
project_root = os.path.abspath(os.path.join(current_dir, ".."))  # Go one level up
sys.path.append(project_root)  # Add the project root to sys.path


from mcp_client.security_manager import SecurityManager

# Load environment variables
load_dotenv("../.env")

class MCPOpenAIClient:

    def __init__(self, model: str = "gpt-4o"):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
        """
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI()
        self.model = model
        self.security_manager = SecurityManager()

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
        # Get available tools
        tools = await self.get_mcp_tools()

        # Initial OpenAI API call
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": query}],
            tools=tools,
            tool_choice="auto",
        )

        # Get assistant's response
        assistant_message = response.choices[0].message

        # Initialize conversation with user query and assistant response
        messages = [
            {"role": "user", "content": query},
            assistant_message,
        ]

        # Handle tool calls if present
        if assistant_message.tool_calls:
            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                if await self.security_manager.check_tool_call(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments),
                ):
                    print(f"Tool call {tool_call.function.name} approved.")
                else:
                    print(f"Tool call {tool_call.function.name} denied.")
                    return "Tool call denied by security manager."

                # Execute tool call
                result = await self.session.call_tool(
                    tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                )

                # Add tool response to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.content[0].text,
                    }
                )

            # Get final response from OpenAI with tool results
            final_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="none",  # Don't allow more tool calls
            )

            return final_response.choices[0].message.content

        # No tool calls, just return the direct response
        return assistant_message.content

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


class MCPOpenAIClientStdio(MCPOpenAIClient):
    """Client for interacting with OpenAI models using MCP tools."""

    def __init__(self, model: str = "gpt-4o"):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
        """
        # Initialize session and client objects
        super().__init__(model=model)
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
        print("\nConnected to server with tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")


class MCPOpenAIClientSSE(MCPOpenAIClient):
    """Client for interacting with OpenAI models using MCP tools."""

    def __init__(self, model: str = "gpt-4o"):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
        """
        # Initialize session and client objects
        super().__init__(model=model)

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
        print("\nConnected to server with tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")


async def main():
    """Main entry point for the client."""
    client = MCPOpenAIClientSSE()
    await client.connect_to_server("http://localhost:8050/sse", headers={})

    # Example: Ask about company vacation policy
    query = "What is our company's vacation policy?"
    print(f"\nQuery: {query}")

    response = await client.prompt(query)
    print(f"\nResponse: {response}")

    await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
