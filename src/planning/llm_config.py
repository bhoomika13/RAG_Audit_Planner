"""
BH8 (LLM) - Azure OpenAI GPT-4.1 client configuration.

Reads Azure OpenAI credentials from environment variables (or a local .env
file, never committed / never hard-coded) so the API key is never typed into
chat or source control.

Required environment variables:
    AZURE_OPENAI_API_KEY       - your Azure OpenAI resource key
    AZURE_OPENAI_ENDPOINT      - e.g. https://<resource-name>.openai.azure.com/
    AZURE_OPENAI_DEPLOYMENT    - the deployment name you gave the gpt-4.1 model in Azure
    AZURE_OPENAI_API_VERSION   - optional, defaults to 2024-10-21
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

DEFAULT_API_VERSION = "2024-10-21"


def get_llm(temperature: float = 0.0) -> AzureChatOpenAI:
    missing = [
        name for name in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            "Missing Azure OpenAI environment variable(s): " + ", ".join(missing) +
            ". Set them in a local .env file (see .env.example) before running the LLM planner."
        )

    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION),
        temperature=temperature,
    )
