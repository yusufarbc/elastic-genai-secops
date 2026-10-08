"""Mock LLM provider for CI and local development. NEVER calls a billed API.

Returns a valid triage decision that references the first masked host and user of the
incident, so the end-to-end flow exercises un-masking in case-service.
"""

from __future__ import annotations

import json

from app.provider.base import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    name = "mock"

    @property
    def model_id(self) -> str:
        return "mock-llm-v1"

    async def complete(
        self,
        system_prompt: str,
        data_block: str,
        *,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> LLMResponse:
        try:
            incident = json.loads(data_block)
        except json.JSONDecodeError:
            incident = {}
        host = (incident.get("affected_hosts") or ["the affected host"])[0]
        user = (incident.get("affected_users") or ["the affected user"])[0]
        techniques = incident.get("mitre_techniques") or []
        risk = int(incident.get("risk_score") or 0)
        thresholds = ((75, "critical"), (50, "high"), (25, "medium"), (0, "low"))
        severity = next(s for limit, s in thresholds if risk >= limit)
        content = json.dumps({
            "severity_suggestion": severity,
            "mitre_techniques_confirmed": techniques[:3],
            "false_positive_likelihood": 0.2,
            "summary": f"Mock triage: suspicious activity on {host} by {user}.",
            "recommended_actions": [f"Review recent process activity on {host}",
                                    f"Confirm with {user} whether the activity was expected"],
            "confidence": 0.5,
            "rationale": "Deterministic mock response for CI and local development.",
        })
        return LLMResponse(
            content=content,
            model_id=self.model_id,
            input_tokens=len(system_prompt.split()) + len(data_block.split()),
            output_tokens=len(content.split()),
            latency_ms=1.0,
        )
