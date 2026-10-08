import pytest
from esm_common.contracts import CaseEvent

from app.router import Router, Settings

CASE = {"id": "inc-1", "severity": "high", "review_status": "pending", "affected_hosts": ["PC-1"]}


def event(kind: str, **case) -> CaseEvent:  # type: ignore[no-untyped-def]
    return CaseEvent.model_validate({"event": kind, "case_id": "inc-1", "case": {**CASE, **case}})


class Channel:
    def __init__(self, name: str, fail: bool = False) -> None:
        self.name, self.fail, self.messages = name, fail, []

    async def send(self, message, event) -> None:  # type: ignore[no-untyped-def]
        if self.fail:
            raise RuntimeError("down")
        self.messages.append(message)


class Sink:
    name = "sink"

    def __init__(self, fail: bool = False) -> None:
        self.fail, self.created = fail, []

    async def create(self, message, event) -> str:  # type: ignore[no-untyped-def]
        if self.fail:
            raise RuntimeError("ticketing down")
        self.created.append(event.case_id)
        return f"sink:{event.case_id}"


async def test_new_high_case_notifies_but_does_not_open_ticket() -> None:
    ch, sink = Channel("slack"), Sink()
    out = await Router(Settings(), [ch], [sink]).handle(event("created"))
    assert out.notified == ["slack"] and sink.created == []
    assert "PC-1" not in ch.messages[0].markdown()  # summary detail by default


async def test_below_min_severity_is_silent() -> None:
    ch = Channel("slack")
    out = await Router(Settings(), [ch], []).handle(event("created", severity="medium"))
    assert out.notified == [] and ch.messages == []


async def test_ticket_only_after_approval() -> None:
    sink = Sink()
    router = Router(Settings(), [], [sink])
    await router.handle(event("reviewed", review_status="rejected"))
    assert sink.created == []
    out = await router.handle(event("reviewed", review_status="approved"))
    assert out.tickets == ["sink:inc-1"]


async def test_failed_channel_does_not_block_others() -> None:
    good = Channel("teams")
    out = await Router(Settings(), [Channel("slack", fail=True), good], []).handle(event("created"))
    assert out.notify_failed == ["slack"] and out.notified == ["teams"]


async def test_ticket_failure_raises_for_redelivery() -> None:
    with pytest.raises(RuntimeError):
        await Router(Settings(ticket_on="created"), [], [Sink(fail=True)]).handle(event("created"))


def test_settings_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TICKET_ON", "always")
    with pytest.raises(ValueError):
        Settings.from_env()
