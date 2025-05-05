import os

class Config:

    """Configuration class for the MCP server and OpenAI client."""

    ENV = os.getenv("ENV", "dev")
    CONSUMER_ID = os.getenv("CONSUMER_ID", "27e185cc-6b29-48e8-98b3-deba9b9eb3b5")
    LLM_PRIVATE_KEY_PATH = os.getenv("LLM_PRIVATE_KEY_PATH", "private_key.pem")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://wmtllmgateway.stage.walmart.com/wmtllmgateway")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")