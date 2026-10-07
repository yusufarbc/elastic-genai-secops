"""LLM provider interface (ADR-018).

llm-orchestrator is the ONLY service that calls an LLM. Business logic depends on this
interface only; vendor specifics live in the provider modules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class LLMProvider(ABC):
    name: str = "base"

    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        data_block: str,
        *,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> LLMResponse:
        """Send the system prompt and the (already masked) data block; return raw text.

        Implementations must keep the two separate: the data block goes into its own
        user message wrapped in <data> tags, never into the system instructions.
        """


def wrap_data(data_block: str) -> str:
    return f"<data>\n{data_block}\n</data>"
