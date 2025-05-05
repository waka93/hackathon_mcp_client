import os

class Config:

    """Configuration class for the MCP server and OpenAI client."""

    ENV = os.getenv("ENV", "dev")
    LOG_LEVEL = "INFO"
    CONSUMER_ID = os.getenv("CONSUMER_ID", "27e185cc-6b29-48e8-98b3-deba9b9eb3b5")
    LLM_PRIVATE_KEY_PATH = os.getenv("LLM_PRIVATE_KEY_PATH", "private_key.pem")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://wmtllmgateway.stage.walmart.com/wmtllmgateway")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    TOOL_POLICIES = {
        "confluence_search": {"requires_approval": False, "max_calls_per_minute": 20},
        "confluence_get_page": {"requires_approval": False, "max_calls_per_minute": 20},
        "confluence_get_page_children": {"requires_approval": False, "max_calls_per_minute": 20},
        "confluence_get_page_ancestors": {"requires_approval": False, "max_calls_per_minute": 20},
        "confluence_get_comments": {"requires_approval": False, "max_calls_per_minute": 20},
        "confluence_get_labels": {"requires_approval": False, "max_calls_per_minute": 20},
        "confluence_create_page": {"requires_approval": True, "max_calls_per_minute": 5},
        "confluence_update_page": {"requires_approval": True, "max_calls_per_minute": 5},
        "confluence_delete_page": {"requires_approval": True, "max_calls_per_minute": 5},
        "confluence_add_label": {"requires_approval": True, "max_calls_per_minute": 5},
    }

    DEFAULT_TOOL_POLICY = {"requires_approval": True, "max_calls_per_minute": 5}

    SYSTEM_PROMPT = \
"""
You are MyAssistant, an AI client that helps with searching, creating and updating CONFLUENCE pages.
You have access to a set of tools that are executed upon the user's approval. You can use one tool per message, and will receive the result of that tool use in the user's response. You use tools step-by-step to accomplish a given task, with each tool use informed by the result of the previous tool use.

When searching pages, make sure to put `space` in a separate argument other than the query itself.
When searching pages, make sure you return the page link as well.
When user requests to get page content, you must search for the page ID (INTEGER) first if not provided by the user, and then get the page content using the page ID.
When user requests to update a confluence page, you must search for the page ID (INTEGER), first if not provided by the user, and then update the page with the page ID.

User prefer to work under one confluence space. Make sure to remember the space and use it in the subsequent conversations unless the user change it specifically.
"""
