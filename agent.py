import logging

import httpx
from agents import Agent, Runner, OpenAIChatCompletionsModel
from agents.mcp import MCPServer, MCPServerSse
from agents.model_settings import ModelSettings
from openai import AsyncAzureOpenAI

from config import Config
from utils import generate_headers
from cache import CACHE


async def main():
    headers = generate_headers(
        private_key_path=Config.LLM_PRIVATE_KEY_PATH,
        consumer_id=Config.CONSUMER_ID,
        env=Config.ENV,
    )

    openai_client = AsyncAzureOpenAI(
        api_key=Config.CONSUMER_ID,
        api_version=Config.AZURE_OPENAI_API_VERSION,
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        http_client = httpx.AsyncClient(verify=False, headers=headers)
    )

    confluence_mcp = MCPServerSse(
        name="Confluence MCP server",
        params={
            "url": Config.CONFLUENCE_MCP_SERVER,
        },
        cache_tools_list=True,
    )
    # await confluence_mcp.connect()

    agent = Agent(
        name="Confluence MCP (Model Context Protocol) agent",
        instructions=Config.CONFLUENCE_SYSTEM_PROMPT,
        model=OpenAIChatCompletionsModel(
            model="gpt-4o",
            openai_client=openai_client
        ),
        model_settings=ModelSettings(tool_choice="auto"),
        mcp_servers=[
            confluence_mcp,
        ]
    )
    await confluence_mcp.connect()

    conversations = []

    while True:
        try:
            logging.warning("Enter your question:")
            query = input().strip().lower()
            conversations.append({"role": "user", "content": query})
            logging.warning(f"Chat history: {conversations}")
            result = await Runner.run(starting_agent=agent, input=conversations)
            conversations =result.to_input_list()
            logging.warning(f"Agent response: {result.final_output}")

        except KeyboardInterrupt:
            await confluence_mcp.cleanup()
            break


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())