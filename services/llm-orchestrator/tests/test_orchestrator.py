import json
from datetime import UTC, datetime

import pytest
from esm_common.contracts import MaskedIncident

from app.audit import AuditLogger
from app.orchestrator import SYSTEM_PROMPT, BudgetTracker, LLMOrchestrator, parse_response
from app.provider.base import LLMProvider, LLMResponse
from app.provider.mock import MockLLMProvider

INCIDENT = MaskedIncident(
    incident_id="inc-1", created_at=datetime(2026, 10, 7, tzinfo=UTC),
    summary="1 alert(s); hosts: host_1a2b3c", affected_hosts=["host_1a2b3c"],
    affected_users=["user_4d5e6f"], mitre_techniques=["T1059"], risk_score=60, alert_count=1,
)


class ScriptedProvider(LLMProvider):
    """Returns the given responses in order (str) or raises them (Exception)."""

    name = "scripted"

    def __init__(self, *responses: str | Exception) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    @property
    def model_id(self) -> str:
        return "scripted-1"

    async def complete(self, system_prompt, data_block, *, temperature=0.2,
                       max_output_tokens=1024):  # type: ignore[no-untyped-def]
        self.calls.append((system_prompt, data_block))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return LLMResponse(content=r, model_id="scripted-1", input_tokens=100, output_tokens=50,
                           latency_ms=5.0)


class RecordingAudit(AuditLogger):
    def __init__(self) -> None:
        super().__init__(None)
        self.outcomes: list[str] = []

    async def record(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.outcomes.append(args[6])


VALID = json.dumps({
    "severity_suggestion": "high", "mitre_techniques_confirmed": ["T1059"],
    "false_positive_likelihood": 0.1, "summary": "Macro on host_1a2b3c",
    "recommended_actions": ["Isolate host_1a2b3c"], "confidence": 0.7, "rationale": "r",
})


def orchestrator(provider: LLMProvider,
                 budget: int = 10_000) -> tuple[LLMOrchestrator, RecordingAudit]:
    audit = RecordingAudit()
    return LLMOrchestrator(provider, BudgetTracker(budget, 3600), audit), audit


async def test_valid_response_becomes_decision() -> None:
    provider = ScriptedProvider(VALID)
    orch, audit = orchestrator(provider)
    result = await orch.triage(INCIDENT)
    assert result.status == "triaged" and result.decision is not None
    assert result.decision.severity_suggestion == "high"
    assert result.decision.input_tokens == 100
    assert audit.outcomes == ["triaged"]
    system, data = provider.calls[0]
    assert system == SYSTEM_PROMPT and json.loads(data)["incident_id"] == "inc-1"


async def test_invalid_then_valid_is_retried() -> None:
    bad_schema = '{"severity_suggestion": "extreme"}'
    orch, audit = orchestrator(ScriptedProvider("not json", bad_schema, VALID))
    result = await orch.triage(INCIDENT)
    assert result.status == "triaged"
    assert audit.outcomes == ["failed", "failed", "triaged"]


async def test_persistent_failure_reports_llm_failed() -> None:
    orch, _ = orchestrator(ScriptedProvider(RuntimeError("down"), RuntimeError("down"),
                                            RuntimeError("down")))
    result = await orch.triage(INCIDENT)
    assert result.status == "llm_failed" and result.decision is None
    assert "down" in result.error and result.incident.incident_id == "inc-1"


async def test_budget_exhausted_skips_llm() -> None:
    provider = ScriptedProvider(VALID, VALID)
    orch, _ = orchestrator(provider, budget=100)
    assert (await orch.triage(INCIDENT)).status == "triaged"  # uses 150 tokens
    result = await orch.triage(INCIDENT)
    assert result.status == "budget_exceeded" and len(provider.calls) == 1


def test_budget_window_resets() -> None:
    now = [0.0]
    budget = BudgetTracker(100, 60, clock=lambda: now[0])
    budget.record(150)
    assert not budget.allow()
    now[0] = 61
    assert budget.allow() and budget.used == 0


def test_parse_response_tolerates_fences_and_drops_extra_keys() -> None:
    raw = parse_response('```json\n{"summary": "s", "incident_id": "spoofed", "x": 1}\n```')
    assert raw == {"summary": "s"}
    with pytest.raises(ValueError):
        parse_response("no json here")


async def test_mock_provider_output_validates() -> None:
    orch, _ = orchestrator(MockLLMProvider())
    result = await orch.triage(INCIDENT)
    assert result.status == "triaged" and result.decision is not None
    assert "host_1a2b3c" in result.decision.summary
    assert result.decision.severity_suggestion == "high"
