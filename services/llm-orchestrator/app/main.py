"""llm-orchestrator: esm.masked-incidents -> LLM triage -> esm.triage-decisions.

The only service that calls an LLM. Every masked incident produces exactly one TriageResult,
also when the budget is exhausted or the LLM fails, so no incident is lost.
"""

from __future__ import annotations

import asyncio
import os
import signal

from esm_common import bus as busmod
from esm_common.contracts import SUBJECT_MASKED_INCIDENTS, SUBJECT_TRIAGE_RESULTS, MaskedIncident
from esm_common.logging import configure
from pydantic import ValidationError

from app.audit import AuditLogger
from app.orchestrator import BudgetTracker, LLMOrchestrator
from app.provider import build_provider

log = configure("llm-orchestrator")


async def main() -> None:
    provider = build_provider()
    budget = BudgetTracker(
        max_tokens_per_window=int(os.getenv("LLM_MAX_TOKENS_PER_WINDOW", "500000")),
        window_seconds=float(os.getenv("LLM_BUDGET_WINDOW_SECONDS", "3600")),
    )
    audit = AuditLogger.from_env()
    orchestrator = LLMOrchestrator(provider, budget, audit)
    bus = await busmod.from_env()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    async def handle(data: bytes) -> None:
        try:
            incident = MaskedIncident.model_validate_json(data)
        except ValidationError as exc:
            log.error("invalid masked incident, dropping", error=str(exc))
            return
        result = await orchestrator.triage(incident)
        await bus.publish(SUBJECT_TRIAGE_RESULTS, result, msg_id=incident.incident_id)
        log.info("triage result published", incident_id=incident.incident_id,
                 status=result.status, budget_used=budget.used)

    log.info("llm-orchestrator started", provider=provider.name, model=provider.model_id)
    try:
        await bus.subscribe(SUBJECT_MASKED_INCIDENTS, "llm-orchestrator", handle, stop)
    finally:
        await audit.close()
        await bus.close()
        log.info("llm-orchestrator stopped")


if __name__ == "__main__":
    asyncio.run(main())
