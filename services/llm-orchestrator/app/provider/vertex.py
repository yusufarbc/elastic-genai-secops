"""Gemini on GCP Vertex AI (ADR-005/006). Optional: pip install "llm-orchestrator[vertex]".

Credentials come from Workload Identity on GKE (no key files). GCP_PROJECT and
VERTEX_LOCATION select the endpoint; the model comes from LLM_MODEL_ID.
"""

from __future__ import annotations

import os
import time

from app.provider.base import LLMProvider, LLMResponse, wrap_data


class VertexAIProvider(LLMProvider):
    name = "vertex"

    def __init__(self, model_id: str) -> None:
        if not model_id:
            raise ValueError("LLM_MODEL_ID is required for provider vertex")
        project = os.getenv("GCP_PROJECT", "")
        if not project:
            raise ValueError("GCP_PROJECT is required for provider vertex")
        import vertexai  # type: ignore[import-untyped]
        from vertexai.generative_models import GenerativeModel  # type: ignore[import-untyped]

        vertexai.init(project=project, location=os.getenv("VERTEX_LOCATION", "us-central1"))
        self._model_id = model_id
        self._model_factory = GenerativeModel

    @property
    def model_id(self) -> str:
        return self._model_id

    async def complete(self, system_prompt: str, data_block: str, *, temperature: float = 0.2,
                       max_output_tokens: int = 1024) -> LLMResponse:
        from vertexai.generative_models import GenerationConfig  # type: ignore[import-untyped]

        model = self._model_factory(self._model_id, system_instruction=system_prompt)
        config = GenerationConfig(temperature=temperature, max_output_tokens=max_output_tokens,
                                  response_mime_type="application/json")
        t0 = time.monotonic()
        response = await model.generate_content_async(wrap_data(data_block),
                                                      generation_config=config)
        usage = response.usage_metadata
        return LLMResponse(
            content=response.text,
            model_id=self._model_id,
            input_tokens=usage.prompt_token_count,
            output_tokens=usage.candidates_token_count,
            latency_ms=(time.monotonic() - t0) * 1000,
        )
