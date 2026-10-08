"""HTTP providers implemented with httpx (no vendor SDKs): Ollama, OpenAI-compatible, Anthropic."""

from __future__ import annotations

import time

import httpx

from app.provider.base import LLMProvider, LLMResponse, wrap_data


class _HTTPProvider(LLMProvider):
    def __init__(self, model_id: str, base_url: str, api_key: str = "",
                 client: httpx.AsyncClient | None = None, timeout: float = 120.0) -> None:
        if not model_id:
            raise ValueError("LLM_MODEL_ID is required for provider " + self.name)
        self._model = model_id
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)

    @property
    def model_id(self) -> str:
        return self._model

    async def _post(self, path: str, body: dict, headers: dict[str, str]) -> tuple[dict, float]:
        t0 = time.monotonic()
        resp = await self._client.post(path, json=body, headers=headers)
        latency = (time.monotonic() - t0) * 1000
        resp.raise_for_status()
        return resp.json(), latency


class OllamaProvider(_HTTPProvider):
    """Local models through Ollama's /api/chat (air-gapped installs)."""

    name = "ollama"

    async def complete(self, system_prompt: str, data_block: str, *, temperature: float = 0.2,
                       max_output_tokens: int = 1024) -> LLMResponse:
        data, latency = await self._post("/api/chat", {
            "model": self._model,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": max_output_tokens},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": wrap_data(data_block)},
            ],
        }, {})
        return LLMResponse(
            content=data["message"]["content"],
            model_id=data.get("model", self._model),
            input_tokens=int(data.get("prompt_eval_count", 0)),
            output_tokens=int(data.get("eval_count", 0)),
            latency_ms=latency,
        )


class OpenAICompatibleProvider(_HTTPProvider):
    """OpenAI, Azure OpenAI, vLLM, LM Studio and other /chat/completions servers."""

    name = "openai-compatible"

    async def complete(self, system_prompt: str, data_block: str, *, temperature: float = 0.2,
                       max_output_tokens: int = 1024) -> LLMResponse:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        data, latency = await self._post("/chat/completions", {
            "model": self._model,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": wrap_data(data_block)},
            ],
        }, headers)
        usage = data.get("usage") or {}
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model_id=data.get("model", self._model),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            latency_ms=latency,
        )


class AnthropicProvider(_HTTPProvider):
    """Claude models through the Anthropic Messages API."""

    name = "anthropic"
    API_VERSION = "2023-06-01"

    async def complete(self, system_prompt: str, data_block: str, *, temperature: float = 0.2,
                       max_output_tokens: int = 1024) -> LLMResponse:
        if not self._api_key:
            raise ValueError("LLM_API_KEY is required for the anthropic provider")
        data, latency = await self._post("/v1/messages", {
            "model": self._model,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": wrap_data(data_block)}],
        }, {"x-api-key": self._api_key, "anthropic-version": self.API_VERSION})
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        usage = data.get("usage") or {}
        return LLMResponse(
            content=text,
            model_id=data.get("model", self._model),
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            latency_ms=latency,
        )
