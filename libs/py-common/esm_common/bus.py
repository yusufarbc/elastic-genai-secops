"""Message bus abstraction (ADR-017) with a NATS JetStream implementation.

Semantics match libs/go-common/bus: one stream "ESM" with subjects "esm.>", durable pull
consumers, explicit acks, redelivery on handler errors, and esm.dlq after MAX_DELIVER attempts.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Protocol

import structlog
from pydantic import BaseModel

from esm_common.contracts import SUBJECT_DLQ

logger = structlog.get_logger(__name__)

STREAM = "ESM"
MAX_DELIVER = 5

Handler = Callable[[bytes], Awaitable[None]]


class Bus(Protocol):
    async def publish(self, subject: str, message: BaseModel | dict, msg_id: str = "") -> None: ...

    async def subscribe(self, subject: str, durable: str, handler: Handler,
                        stop: asyncio.Event) -> None: ...

    async def close(self) -> None: ...


def _encode(message: BaseModel | dict) -> bytes:
    if isinstance(message, BaseModel):
        return message.model_dump_json().encode()
    return json.dumps(message, default=str).encode()


class NatsBus:
    def __init__(self, nc, js) -> None:  # type: ignore[no-untyped-def]
        self._nc = nc
        self._js = js

    @classmethod
    async def connect(cls, url: str) -> NatsBus:
        import nats
        from nats.js.api import StreamConfig
        from nats.js.errors import BadRequestError

        while True:
            try:
                nc = await nats.connect(url, max_reconnect_attempts=-1, reconnect_time_wait=2)
                break
            except Exception as exc:  # NATS not up yet
                logger.warning("waiting for NATS", url=url, error=str(exc))
                await asyncio.sleep(2)
        js = nc.jetstream()
        config = StreamConfig(name=STREAM, subjects=["esm.>"], max_age=7 * 24 * 3600,
                              duplicate_window=600)
        try:
            await js.add_stream(config)
        except BadRequestError:
            await js.update_stream(config)
        return cls(nc, js)

    async def publish(self, subject: str, message: BaseModel | dict, msg_id: str = "") -> None:
        # Duplicate detection is per stream and all subjects share ESM: scope the ID to the subject
        headers = {"Nats-Msg-Id": f"{subject}:{msg_id}"} if msg_id else None
        ack = await self._js.publish(subject, _encode(message), headers=headers)
        if ack.duplicate:
            logger.info("duplicate publish ignored by JetStream", subject=subject, msg_id=msg_id)

    async def subscribe(self, subject: str, durable: str, handler: Handler,
                        stop: asyncio.Event) -> None:
        from nats.errors import TimeoutError as NatsTimeout
        from nats.js.api import AckPolicy, ConsumerConfig

        sub = await self._js.pull_subscribe(
            subject, durable=durable, stream=STREAM,
            config=ConsumerConfig(ack_policy=AckPolicy.EXPLICIT, ack_wait=300,
                                  max_deliver=MAX_DELIVER),
        )
        while not stop.is_set():
            try:
                msgs = await sub.fetch(10, timeout=2)
            except (TimeoutError, NatsTimeout):
                continue
            for msg in msgs:
                try:
                    await handler(msg.data)
                    await msg.ack()
                except Exception as exc:
                    delivered = msg.metadata.num_delivered if msg.metadata else 0
                    if delivered >= MAX_DELIVER:
                        logger.error("message failed permanently, sending to DLQ",
                                     subject=subject, error=str(exc))
                        await self.publish(SUBJECT_DLQ, {
                            "subject": subject, "consumer": durable, "error": str(exc),
                            "data": msg.data.decode(errors="replace"),
                        })
                        await msg.term()
                    else:
                        logger.warning("message failed, will retry", subject=subject,
                                       error=str(exc), delivered=delivered)
                        await msg.nak(delay=5)

    async def close(self) -> None:
        await self._nc.drain()


async def from_env() -> Bus:
    backend = os.getenv("BUS_BACKEND", "nats")
    if backend == "nats":
        return await NatsBus.connect(os.getenv("NATS_URL", "nats://nats:4222"))
    # The GCP Pub/Sub adapter is planned (ADR-017); see ROADMAP.md.
    raise ValueError(f"unsupported BUS_BACKEND {backend!r} (supported: nats)")
