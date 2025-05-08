"""
Module: hackathon_mcp_client.app

This module is the entry point of the hackathon_mcp_client application.

It sets up the FastAPI application, configures the middleware, defines the routes, and starts the server.

This module also includes a custom Swagger UI endpoint and a health check route.
"""

import logging
import os

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from agents.mcp import MCPServerSse

from schema import InputDataModel
from agent import MCPAgent
from config import Config

with open("VERSION") as f:
    PROJECT_VERSION = f.read()

API_VERSION = "v1"  # Temp while figure out configuration files and imports

app = FastAPI(
    title="hackathon_mcp_client",
    version=PROJECT_VERSION,
    openapi_prefix=os.getenv("ROOT_PATH", ""),
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
app.logger = logger


@app.post("/prompt", include_in_schema=True)
async def prompt(data: InputDataModel, request: Request, response: Response):
    query = data.userInput
    conversation_id = data.conversationId
    chat_history = data.chatHistory
    response_payload = {}
    try:
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
            conversation_cache=True,
            cache_key=conversation_id,
        )
        await agent.connect()
        client_response = await agent.prompt(query)
        await agent.cleanup()

        response_payload["modelResponse"] = client_response
        response_payload["statusText"] = "Success!"
        response_payload["statusCode"] = status.HTTP_200_OK
        response_payload["responseType"] = "markdown"
        response_payload["responseAttribute"] = {}
        response.status_code = 200

    except Exception as e:
        logging.error(e)
        response_payload["modelResponse"] = f"Display error message for hackathon only: {str(e)}"
        response_payload["statusText"] = f"Display error message for hackathon only: {str(e)}"
        response_payload["statusCode"] = status.HTTP_200_OK
        response.status_code = 424

    return response_payload


@app.get("/doc", include_in_schema=False)
async def custom_swagger_ui_html(req: Request):
    """
    Returns the HTML for the custom Swagger UI.

    Args:
        req (Request): The request object.

    Returns:
        str: The HTML for the custom Swagger UI.
    """
    logger.debug(f"Swagger endpoint: {str(req.base_url)}")

    if "people-data-science" in str(req.base_url):
        logger.debug(f"Found non-local swagger endpoint: {str(req.base_url)}")
        openapi_url = str(req.base_url).rstrip("/") + str(app.openapi_url)
        openapi_url = "https" + openapi_url[4:]
    else:
        root_path = req.scope.get("root_path", "").rstrip("/")
        openapi_url = root_path + app.openapi_url

    logger.debug(f"Swagger Endpoint: {openapi_url}")

    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title="Swagger",
    )


# Liveness probe health route
@app.get("/healthz/live")
@app.get("/healthz/ready")
async def health_check():
    """
    This is an asynchronous Python function that returns the string "OK" and can be used for health
    checks.
    :return: the string "OK".
    """
    return "OK"


if __name__ == "__main__":
    uvicorn.run(app)
