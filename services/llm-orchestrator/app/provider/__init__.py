"""Provider selection (ADR-018). Configuration comes from the environment:

LLM_PROVIDER   mock | ollama | openai-compatible | anthropic | vertex   (default mock)
LLM_MODEL_ID   model name, required for every provider except mock
LLM_BASE_URL   API base URL (defaults: ollama http://ollama:11434,
               openai-compatible https://api.openai.com/v1, anthropic https://api.anthropic.com)
LLM_API_KEY    API key for openai-compatible and anthropic
"""

from __future__ import annotations

import os

from app.provider.base import LLMProvider, LLMResponse
from app.provider.http import AnthropicProvider, OllamaProvider, OpenAICompatibleProvider
from app.provider.mock import MockLLMProvider

_DEFAULT_URLS = {
    "ollama": "http://ollama:11434",
    "openai-compatible": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}


def build_provider(name: str | None = None) -> LLMProvider:
    name = name or os.getenv("LLM_PROVIDER", "mock")
    model = os.getenv("LLM_MODEL_ID", "")
    if name == "mock":
        return MockLLMProvider()
    if name == "vertex":
        from app.provider.vertex import VertexAIProvider  # optional dependency

        return VertexAIProvider(model)
    classes = {"ollama": OllamaProvider, "openai-compatible": OpenAICompatibleProvider,
               "anthropic": AnthropicProvider}
    if name not in classes:
        raise ValueError(f"unknown LLM_PROVIDER {name!r}")
    return classes[name](model_id=model,
                         base_url=os.getenv("LLM_BASE_URL", _DEFAULT_URLS[name]),
                         api_key=os.getenv("LLM_API_KEY", ""))


__all__ = ["LLMProvider", "LLMResponse", "MockLLMProvider", "build_provider"]
