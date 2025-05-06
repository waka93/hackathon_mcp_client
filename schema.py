"""
This module contains the schema classes for the genai_plugin_prompt_bridge.

It uses the `pydantic` library to create the schema classes.

Classes:
    - ModelConfigs: Represents the configuration for the model.
    - InputDataModel: Represents the input data for the prompt.
    - ChatOutputDataModel: Represents the output data of the chat.

"""

from typing import List, Optional

from pydantic import AliasChoices, BaseModel, Field, root_validator, validator


class ModelConfigs(BaseModel):
    """
    Represents the configuration for the model.

    Attributes:
        system_prompt (str): The system prompt.
        model (Optional[dict]): The model configuration.
        max_turns (int): The maximum number of turns.
        metadata (Optional[dict]): Future metadata, currently unused.
    """

    system_prompt: str = None
    model: Optional[dict] = {}
    max_turns: int = 10
    # Future metadata, currently unused
    metadata: Optional[dict] = {}


class SourceLabels(BaseModel):
    """
    Configurations for the banner and reference

    Attributes:
        callout_text (str): The text to display when mouse hovers over the icon.
        icon (str): The icon to display.
        source_type (str): The text for the banner
        reference_position (str): The position of the reference.
    """

    callout_text: str = None
    icon: str = None
    source_type: str = None
    reference_position: str = "bottom"


class InputDataModel(BaseModel):
    """
    Represents the input data for the prompt.

    Attributes:
        userInput (str): The user input.
        conversationId (str): The conversation ID.
        channelId (str): The channel ID.
        chatHistory (list[dict]): The chat history.
        model_configs (ModelConfigs): The model configuration.
        source_labels (SourceLabels): The source labels for banner and reference display.
        experienceUUID (Optional[str]): The UUID of the entity calling PB.
        stream (Optional[bool]): The stream field.

    Config:
        arbitrary_types_allowed (bool): Whether to allow arbitrary types.

    Methods:
        validate_injection(cls, value): Validates injection in UserInput.
        validate_feature_flags(cls, values): Validates correct values for schema.
    """

    userInput: str = Field(..., description="User input field")
    conversationId: str = Field(..., description="Conversation ID field")
    channelId: str = Field(..., description="Channel ID field")
    chatHistory: list[dict] = Field(default=[], description="Chat history field")
    model_configs: ModelConfigs
    source_labels: SourceLabels = Field(
        default=SourceLabels(),
        description="Source labels for banner and reference display",
    )
    experienceUUID: Optional[str] = Field(
        default="27e185cc-6b29-48e8-98b3-deba9b9eb3b5",
        description="UUID of the entity that is calling PB",
        validation_alias=AliasChoices("experienceUUID", "entityUUID", "pluginUUID"),
    )
    stream: Optional[bool] = Field(default=False, description="Stream field")
    modelName: Optional[str] = Field(
        default="General LLM", description="Model name field"
    )

    files: Optional[List] = Field(default=[], description="File name field")

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    @validator("userInput")
    def validate_injection(cls, value):
        """
        Validator function for injection in UserInput.

        Args:
            value (str): The user input value.

        Returns:
            str: The user input value.

        Raises:
            ValueError: If HTML injection is detected.
        """
        if "<script>" in value:
            raise ValueError("Invalid input: HTML injection detected")
        return value

    @root_validator(pre=True)
    def validate_feature_flags(cls, values):
        """
        Root validator function to check correct values for schema.

        Args:
            values (dict): The values for the schema.

        Returns:
            dict: The values for the schema.

        Raises:
            ValueError: If any of the required fields are empty.
        """
        if values.get("requestId") == "":
            raise ValueError("requestId cannot be empty")
        if values.get("channelId") == "":
            raise ValueError("channelId cannot be empty")
        if values.get("userInput") == "":
            raise ValueError("userInput cannot be empty")
        if values.get("conversationId") == "":
            raise ValueError("conversationId cannot be empty")
        if values.get("identityToken") == "":
            raise ValueError("identityToken cannot be empty")
        return values


class ChatOutputDataModel(BaseModel):
    """_summary_
    Args:
        BaseModel (_type_): _description_
    Raises:
        ValueError: _description_
        ValueError: _description_
    Returns:
        _type_: _description_
    """

    messageId: str = Field(..., description="Message ID field")
    statusText: str = Field(..., description="Request status")
    statusCode: int = Field(..., description="Request status code")
    modelResponse: str = Field(
        ..., description="String value with model's response to user input"
    )
    intermediateSteps: list[dict] = Field(
        default=[], description="List of dictionaries detailing chat process"
    )
