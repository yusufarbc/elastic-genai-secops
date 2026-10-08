"""Request/response mapping of the HTTP providers, using httpx.MockTransport (no network)."""

import json

import httpx
import pytest

from app.provider import build_provider
from app.provider.http import AnthropicProvider, OllamaProvider, OpenAICompatibleProvider


def client(handler, base: str) -> httpx.AsyncClient:  # type: ignore[no-untyped-def]
    return httpx.AsyncClient(base_url=base, transport=httpx.MockTransport(handler))


async def test_ollama() -> None:
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(path=req.url.path, body=json.loads(req.content))
        return httpx.Response(200, json={"model": "llama3.1:8b", "message": {"content": "{}"},
                                         "prompt_eval_count": 12, "eval_count": 3})

    p = OllamaProvider("llama3.1:8b", "http://ollama", client=client(handler, "http://ollama"))
    r = await p.complete("SYS", "DATA")
    assert seen["path"] == "/api/chat" and seen["body"]["format"] == "json"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "SYS"}
    assert seen["body"]["messages"][1]["content"] == "<data>\nDATA\n</data>"
    assert (r.input_tokens, r.output_tokens, r.content) == (12, 3, "{}")


async def test_openai_compatible() -> None:
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(path=req.url.path, auth=req.headers.get("authorization"),
                    body=json.loads(req.content))
        return httpx.Response(200, json={"model": "gpt-x", "usage": {"prompt_tokens": 7,
                                         "completion_tokens": 2},
                                         "choices": [{"message": {"content": "{\"a\":1}"}}]})

    p = OpenAICompatibleProvider("gpt-x", "http://api/v1", api_key="k",
                                 client=client(handler, "http://api/v1"))
    r = await p.complete("SYS", "DATA")
    assert seen["path"] == "/v1/chat/completions" and seen["auth"] == "Bearer k"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert (r.content, r.input_tokens, r.output_tokens) == ('{"a":1}', 7, 2)


async def test_anthropic() -> None:
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(path=req.url.path, key=req.headers.get("x-api-key"),
                    version=req.headers.get("anthropic-version"), body=json.loads(req.content))
        return httpx.Response(200, json={
            "model": "claude-x",
            "content": [{"type": "text", "text": "{\"b\":2}"}],
            "usage": {"input_tokens": 9, "output_tokens": 4},
        })

    p = AnthropicProvider("claude-x", "http://anthropic", api_key="secret",
                          client=client(handler, "http://anthropic"))
    r = await p.complete("SYS", "DATA")
    assert seen["path"] == "/v1/messages" and seen["key"] == "secret"
    assert seen["version"] == AnthropicProvider.API_VERSION
    assert seen["body"]["system"] == "SYS"
    assert seen["body"]["messages"] == [{"role": "user", "content": "<data>\nDATA\n</data>"}]
    assert (r.content, r.input_tokens, r.output_tokens) == ('{"b":2}', 9, 4)


def test_model_id_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL_ID", "")
    with pytest.raises(ValueError):
        build_provider("ollama")
    assert build_provider("mock").model_id == "mock-llm-v1"
    with pytest.raises(ValueError):
        build_provider("nope")
