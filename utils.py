#!/usr/bin/env python

import orjson
import time
import os
import logging
import tiktoken
from base64 import b64encode

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5


def get_timestamp() -> int:
    """Create timestamp

    Returns:
        int: timestamp
    """
    return int(time.time()) * 1000


def sign_data(
    private_key_path: str = None, data: str = None, is_content: bool = False, private_key_content: str = None
) -> bytes:
    """Create authorization signature

    Args:
        private_key_path (str): Path to private key file
        data (str): Additional information needed to generate key in format:
            consumer_id
            timestamp
            key version
        is_content (bool): Whether to use private_key_content instead of reading from a file
        private_key_content (str): Private key content as a string when is_content=True

    Returns:
        bytes: authorization signature

    Raises:
        ValueError: If data is not provided
        Exception: If neither private_key_path nor private_key_content is provided
        FileNotFoundError: If private key file doesn't exist when using file path
    """
    if data is None:
        raise ValueError("Data to sign must be provided")

    if not private_key_path and not private_key_content:
        raise ValueError("Either private_key_path or private_key_content must be provided")

    try:
        if is_content:
            # Use the key content directly
            key = private_key_content
            logging.info("Using provided private key content")
        else:
            # Read the key from file
            logging.info("Reading key from file")
            if not os.path.exists(private_key_path):
                raise FileNotFoundError(f"Private key file not found: {private_key_path}")                
            key = open(private_key_path, "r", encoding="utf-8").read()

        rsakey = RSA.importKey(key)
        signer = PKCS1_v1_5.new(rsakey)
        digest = SHA256.new()
        digest.update(data.encode("utf-8"))
        sign = signer.sign(digest)
        return b64encode(sign)
    except Exception as e:
        logging.error(f"Error signing data: {str(e)}")
        raise


def generate_auth_sig(
    consumer_id: str = None,
    private_key_path: str = None,
    key_version: str = "1",
    is_content: bool = False,
    private_key_content: str = None,
):
    """Generate authentication signature

    Args:
        consumer_id (str): Service App. consumer ID
        private_key_path (str): Path to private key path
        key_version (str): SOA key version, defaults to "1"
        is_content (bool): Whether private_key_content contains the key content directly
        private_key_content (str): Private key content if is_content is True

    Returns:
        tuple: epoch_time, auth_signature

    Raises:
        ValueError: If consumer_id is not provided or if neither private_key_path nor private_key_content is provided
    """
    if consumer_id is None:
        raise ValueError("consumer_id must be provided")

    if not is_content and private_key_path is None:
        raise ValueError("private_key_path must be provided when is_content=False")

    if is_content and private_key_content is None:
        raise ValueError("private_key_content must be provided when is_content=True")

    epoch_time = get_timestamp()
    data = f"{consumer_id}\n{epoch_time}\n{key_version}\n"

    if is_content:
        auth_signature = sign_data(private_key_content=private_key_content, data=data, is_content=True).decode()
    else:
        auth_signature = sign_data(private_key_path=private_key_path, data=data, is_content=False).decode()

    return epoch_time, auth_signature

def generate_headers(
    private_key_path: str = None,
    consumer_id: str = None,
    env: str = None,
    x_api_key: str = None,
):
    """Creates WMTLLM specific headers
    https://gecgithub01.walmart.com/MLPlatforms/elementGenAI/wiki/Walmart-LLM-Gateway#mandatory-headers-for-serviceregistry
    Args:
        private_key_path: Path to private key
        consumer_id: Registered consumer Id
        env: LLM Gateway env
        x_api_key: api key
    Returns:
        dict/json format headers
    """
    # If api_key is provided, use it directly
    if x_api_key:
        header = {"X-Api-Key": x_api_key, "Content-Type": "application/json"}
    # If private_key_path, consumer_id, env
    elif private_key_path and consumer_id and env:
        epoch_ts, auth_sig = generate_auth_sig(consumer_id, private_key_path)
        header = {
            "Content-Type": "application/json",
            "WM_CONSUMER.ID": consumer_id,
            "WM_CONSUMER.INTIMESTAMP": str(epoch_ts),
            "WM_SEC.AUTH_SIGNATURE": auth_sig,
            "WM_SEC.KEY_VERSION": "1",
            "WM_SVC.ENV": env,
            "WM_SVC.NAME": "WMTLLMGATEWAY",
        }
    else:
        raise ValueError(
            "Either an api_key must be provided or private_key_path, consumer_id, " "and env must be provided."
        )
    return header


# Cache encoding for reuse
ENCODING_CACHE = {}


def get_encoding(model: str):
    """Get or cache the encoding for a model."""
    if model not in ENCODING_CACHE:
        ENCODING_CACHE[model] = tiktoken.encoding_for_model(model)
    return ENCODING_CACHE[model]


def count_tokens(messages, model="gpt-4"):
    """Count tokens for a list of messages."""
    encoding = get_encoding(model)  # Reuse cached encoding
    start_time = time.time()
    
    # Serialize all messages into a single string
    total_tokens = 0
    for message in messages:
        try:
            # Convert message to JSON string
            message_str = orjson.dumps(message).decode("utf-8")
        except Exception:
            message_str = str(message)
            
        total_tokens += len(encoding.encode(message_str)) 

    elapsed_time = time.time() - start_time
    logging.info(f"Token count for model {model}: {total_tokens} (elapsed time: {elapsed_time:.2f}s)")
    return total_tokens

def format_chat_history(chat_history: list[dict]) -> list[dict]:
    """Format chat history to OpenAI standard
    Parameters:
        chat_history: List[Dict[str, str]]
            user chat history NOT including the latest user prompt
            key         |   value
            messageType |   [USER | SYSTEM]
            createdAt   |   timestamp string
            text        |   string
    Returns:
        List[Dict[str, str]]
        key     | value
        role    | [user | assistant] # we don't have system role type because we handle system prompt seperately
        text    | string
    """
    result = []
    for message in chat_history:
        if message["messageType"] == "USER":
            role = "user"
        else:
            role = "assistant"
        result.append({"role": role, "content": message["text"]})
    return result
