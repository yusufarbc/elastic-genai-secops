"""outbound-service: esm.case-events -> notifications and tickets."""

from __future__ import annotations

import asyncio
import signal

import httpx
from esm_common import bus as busmod
from esm_common.contracts import SUBJECT_CASE_EVENTS, CaseEvent
from esm_common.logging import configure
from esm_outbound.config import notifiers_from_env, ticket_sinks_from_env
from pydantic import ValidationError

from app.router import Router, Settings

log = configure("outbound-service")


async def main() -> None:
    client = httpx.AsyncClient(timeout=20)
    notifiers = notifiers_from_env(client)
    sinks = ticket_sinks_from_env(client)
    settings = Settings.from_env()
    router = Router(settings, notifiers, sinks)
    bus = await busmod.from_env()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    async def handle(data: bytes) -> None:
        try:
            event = CaseEvent.model_validate_json(data)
        except ValidationError as exc:
            log.error("invalid case event, dropping", error=str(exc))
            return
        await router.handle(event)

    log.info("outbound-service started", notifiers=[n.name for n in notifiers],
             ticketing=[s.name for s in sinks], ticket_on=settings.ticket_on,
             notify_min_severity=settings.notify_min_severity)
    try:
        await bus.subscribe(SUBJECT_CASE_EVENTS, "outbound-service", handle, stop)
    finally:
        await client.aclose()
        await bus.close()
        log.info("outbound-service stopped")


if __name__ == "__main__":
    asyncio.run(main())
