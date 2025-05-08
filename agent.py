import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import httpx
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from agents.mcp import MCPServer, MCPServerSse
from agents.model_settings import ModelSettings
from openai import AsyncAzureOpenAI

from config import Config
from utils import generate_headers

set_tracing_disabled(True)

class MCPAgent:
    """Agent class for handling interactions with the MCP server."""

    def __init__(
        self, 
        name: str, 
        model: str, 
        instructions: str, 
        llm_client: AsyncAzureOpenAI = None,
        mcp_servers: list[MCPServer] = [],
    ):
        """
        Initialize the MCPAgent with the given parameters.
        :param name: Name of the agent.
        :param model: Model to be used by the agent.
        :param instructions: Instructions for the agent.
        :param llm_client: LLM client for the agent.
        :param mcp_servers: List of MCP servers to connect to.
        :param conversation_cache: Whether to cache conversations.
        :param cache_key: Key for the conversation cache.
        """

        if llm_client is None:
            headers = generate_headers(
                private_key_path=Config.LLM_PRIVATE_KEY_PATH,
                consumer_id=Config.CONSUMER_ID,
                env=Config.ENV,
            )
            llm_client = AsyncAzureOpenAI(
                api_key=Config.CONSUMER_ID,
                api_version=Config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                http_client = httpx.AsyncClient(verify=False, headers=headers)
            )
        self.agent = Agent(
            name=name,
            instructions=instructions,
            model=OpenAIChatCompletionsModel(
                model=model,
                openai_client=llm_client
            ),
            model_settings=ModelSettings(tool_choice="auto"),
            mcp_servers=mcp_servers
        )

    async def connect(self):
        """Connect to the MCP server."""
        for server in self.agent.mcp_servers:
            await server.connect()

    async def cleanup(self):
        """Clean up the MCP server connections."""
        for server in self.agent.mcp_servers:
            await server.cleanup()

    async def prompt(self, messages: list[dict]):
        """Prompt the agent with a query."""
        result = await Runner.run(starting_agent=self.agent, input=messages)
        return result.final_output

async def main():
    agent = MCPAgent(
        name="Confluence MCP (Model Context Protocol) agent",
        model="gpt-4o",
        instructions=Config.CONFLUENCE_SYSTEM_PROMPT,
        llm_client=None,
        mcp_servers=[
            MCPServerSse(
                name="Confluence MCP server",
                params={
                    "url": Config.CONFLUENCE_MCP_SERVER,
                },
                cache_tools_list=True,
            ),
            MCPServerSse(
                name="Grafana MCP server",
                params={
                    "url": Config.GRAFANA_MCP_SERVER,
                },
                cache_tools_list=True,
            )
        ],
    )
    await agent.connect()

    messages = []
    while True:
        try:
            logging.info("Enter your question:")
            query = input().strip().lower()
            messages.append({"role": "user", "content": query})
            logging.info(f"Chat history: {messages}")
            response = await agent.prompt(messages)
            messages.append({"role": "assistant", "content": response})
            logging.info(f"Agent response: {response}")

        except KeyboardInterrupt:
            await agent.cleanup()
            break


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
