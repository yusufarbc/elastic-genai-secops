"""Decide what each case event triggers.

NOTIFY_ON          events that notify: created, reviewed (default: created)
NOTIFY_MIN_SEVERITY  low | medium | high | critical (default: high)
NOTIFY_DETAIL      summary | full (default: summary - no hosts, users, IPs or free text)
TICKET_ON          approved | created | never (default: approved - only after an analyst approves)
TICKET_DETAIL      summary | full (default: full)
CASE_URL           base URL for case links, e.g. https://soc.example.com/api/cases (optional)

Notifications are best effort: failures are logged, not retried, so a channel outage does not
resend to the channels that worked. Ticket creation is retried (sinks are idempotent per case).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import structlog
from esm_common.contracts import CASE_EVENT_CREATED, CASE_EVENT_REVIEWED, CaseEvent
from esm_outbound.notifiers import Notifier
from esm_outbound.render import meets, render
from esm_outbound.ticketing import TicketSink

logger = structlog.get_logger(__name__)


@dataclass
class Settings:
    notify_on: set[str] = field(default_factory=lambda: {CASE_EVENT_CREATED})
    notify_min_severity: str = "high"
    notify_detail: str = "summary"
    ticket_on: str = "approved"
    ticket_detail: str = "full"
    case_url: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        s = cls(
            notify_on={e.strip() for e in os.getenv("NOTIFY_ON", "created").split(",")
                       if e.strip()},
            notify_min_severity=os.getenv("NOTIFY_MIN_SEVERITY", "high"),
            notify_detail=os.getenv("NOTIFY_DETAIL", "summary"),
            ticket_on=os.getenv("TICKET_ON", "approved"),
            ticket_detail=os.getenv("TICKET_DETAIL", "full"),
            case_url=os.getenv("CASE_URL", ""),
        )
        if s.ticket_on not in ("approved", "created", "never"):
            raise ValueError("TICKET_ON must be approved, created or never")
        for d in (s.notify_detail, s.ticket_detail):
            if d not in ("summary", "full"):
                raise ValueError("NOTIFY_DETAIL / TICKET_DETAIL must be summary or full")
        return s


@dataclass
class Outcome:
    notified: list[str] = field(default_factory=list)
    notify_failed: list[str] = field(default_factory=list)
    tickets: list[str] = field(default_factory=list)


class Router:
    def __init__(self, settings: Settings, notifiers: list[Notifier],
                 sinks: list[TicketSink]) -> None:
        self._s, self._notifiers, self._sinks = settings, notifiers, sinks

    def wants_ticket(self, event: CaseEvent) -> bool:
        if self._s.ticket_on == "created":
            return event.event == CASE_EVENT_CREATED
        if self._s.ticket_on == "approved":
            return event.event == CASE_EVENT_REVIEWED and event.case.review_status == "approved"
        return False

    def wants_notification(self, event: CaseEvent) -> bool:
        return event.event in self._s.notify_on and meets(event.case.severity,
                                                         self._s.notify_min_severity)

    async def handle(self, event: CaseEvent) -> Outcome:
        out = Outcome()
        log = logger.bind(case_id=event.case_id, event=event.event)
        if self._notifiers and self.wants_notification(event):
            message = render(event, self._s.notify_detail, self._s.case_url)
            for n in self._notifiers:
                try:
                    await n.send(message, event)
                    out.notified.append(n.name)
                except Exception as exc:
                    out.notify_failed.append(n.name)
                    log.error("notification failed", channel=n.name, error=str(exc))
        if self._sinks and self.wants_ticket(event):
            message = render(event, self._s.ticket_detail, self._s.case_url)
            for sink in self._sinks:
                out.tickets.append(await sink.create(message, event))  # raises -> redelivery
        if out.notified or out.notify_failed or out.tickets:
            log.info("case event delivered", notified=out.notified, failed=out.notify_failed,
                     tickets=out.tickets)
        return out
