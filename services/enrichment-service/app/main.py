"""enrichment-service: esm.incidents -> curate + mask -> esm.masked-incidents."""

from __future__ import annotations

import asyncio
import os
import signal

from esm_common import bus as busmod
from esm_common.contracts import SUBJECT_INCIDENTS, SUBJECT_MASKED_INCIDENTS, Incident
from esm_common.logging import configure
from esm_outbound.config import threat_intel_from_env
from pydantic import ValidationError

from app.curate import build_masked_incident
from app.masking import MaskingClient

log = configure("enrichment-service")


async def main() -> None:
    masking = MaskingClient(os.getenv("MASKING_SERVICE_URL", "http://masking-service:8001"))
    ti = threat_intel_from_env()
    bus = await busmod.from_env()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    async def handle(data: bytes) -> None:
        try:
            incident = Incident.model_validate_json(data)
        except ValidationError as exc:
            log.error("invalid incident message, dropping", error=str(exc))
            return
        masked = await build_masked_incident(incident, masking.mask, ti)
        await bus.publish(SUBJECT_MASKED_INCIDENTS, masked, msg_id=incident.id)
        log.info("masked incident published", incident_id=incident.id,
                 alerts=incident.alert_count, hosts=len(masked.affected_hosts))

    log.info("enrichment-service started", threat_intel=ti.enabled)
    try:
        await bus.subscribe(SUBJECT_INCIDENTS, "enrichment-service", handle, stop)
    finally:
        await masking.close()
        await bus.close()
        log.info("enrichment-service stopped")


if __name__ == "__main__":
    asyncio.run(main())
