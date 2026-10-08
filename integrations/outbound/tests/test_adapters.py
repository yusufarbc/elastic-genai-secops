import json

import httpx
import pytest
from esm_common.contracts import CaseEvent

from esm_outbound.notifiers import SlackNotifier, TeamsNotifier, WebhookNotifier
from esm_outbound.render import render
from esm_outbound.threatintel import MISP, AbuseIPDB, ThreatIntel, Verdict
from esm_outbound.ticketing import JiraSink, TheHiveSink

EVENT = CaseEvent.model_validate({
    "event": "created", "case_id": "inc-1",
    "case": {"id": "inc-1", "severity": "high", "risk_score": 73, "alert_count": 5,
             "triage_status": "triaged", "review_status": "pending",
             "summary": "Macro on PC-SECRET by alice", "mitre_techniques": ["T1059"],
             "recommended_actions": ["Isolate PC-SECRET"], "affected_hosts": ["PC-SECRET"],
             "affected_users": ["alice"], "source_ips": ["203.0.113.9"],
             "timeline": [{"rule": "[WIN-001] Office spawned shell", "host": "PC-SECRET"}]},
})


def recorder():  # type: ignore[no-untyped-def]
    calls: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(200, json={})
    return calls, httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_summary_detail_has_no_entities() -> None:
    text = render(EVENT, "summary", "https://soc/cases").markdown()
    for secret in ("PC-SECRET", "alice", "203.0.113.9", "Macro"):
        assert secret not in text
    assert "[WIN-001] Office spawned shell" in text and "https://soc/cases/inc-1" in text


def test_full_detail_includes_entities_and_suggestions() -> None:
    text = render(EVENT, "full").plain()
    assert "PC-SECRET" in text and "alice" in text and "Isolate PC-SECRET" in text


async def test_slack_teams_webhook_payloads() -> None:
    calls, client = recorder()
    msg = render(EVENT, "summary", "https://soc/cases")
    await SlackNotifier("https://hooks.slack/x", client).send(msg, EVENT)
    await TeamsNotifier("https://teams/x", client).send(msg, EVENT)
    await WebhookNotifier("https://soar/x", client, token="t0k").send(msg, EVENT)
    slack, teams, hook = (json.loads(c.content) for c in calls)
    assert "*[ESM] HIGH" in slack["text"] and "<https://soc/cases/inc-1|Open case>" in slack["text"]
    card = teams["attachments"][0]["content"]
    assert card["type"] == "AdaptiveCard" and card["actions"][0]["url"].endswith("/inc-1")
    assert hook["case_id"] == "inc-1" and calls[2].headers["authorization"] == "Bearer t0k"


async def test_thehive_is_idempotent() -> None:
    responses = iter([httpx.Response(201, json={"_id": "~123"}),
                      httpx.Response(400, json={"message": "Alert already exists"})])
    seen: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(json.loads(req.content))
        return next(responses)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sink = TheHiveSink("https://hive", "key", client)
    msg = render(EVENT, "full")
    assert await sink.create(msg, EVENT) == "thehive:~123"
    assert "already exists" in await sink.create(msg, EVENT)
    assert seen[0]["sourceRef"] == "inc-1" and seen[0]["severity"] == 3


async def test_jira_searches_before_creating() -> None:
    state = {"exists": False}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/search"):
            assert req.url.params["jql"] == 'labels = "esm-inc-1"'
            issues = [{"key": "SOC-7"}] if state["exists"] else []
            return httpx.Response(200, json={"issues": issues})
        state["exists"] = True
        body = json.loads(req.content)["fields"]
        assert body["project"] == {"key": "SOC"} and "esm-inc-1" in body["labels"]
        return httpx.Response(201, json={"key": "SOC-7"})

    sink = JiraSink("https://jira", "u", "t", "SOC", httpx.AsyncClient(
        transport=httpx.MockTransport(handler)))
    msg = render(EVENT, "full")
    assert await sink.create(msg, EVENT) == "jira:SOC-7"
    assert await sink.create(msg, EVENT) == "jira:SOC-7 (already exists)"


async def test_abuseipdb_and_misp_verdicts() -> None:
    def abuse(req: httpx.Request) -> httpx.Response:
        assert req.headers["key"] == "k" and req.url.params["ipAddress"] == "198.51.100.1"
        return httpx.Response(200, json={"data": {"abuseConfidenceScore": 87}})

    def misp(req: httpx.Request) -> httpx.Response:
        assert json.loads(req.content)["value"] == "198.51.100.1"
        return httpx.Response(200, json={"response": {"Attribute": []}})

    a = AbuseIPDB("k", httpx.AsyncClient(transport=httpx.MockTransport(abuse)))
    m = MISP("https://misp", "k", httpx.AsyncClient(transport=httpx.MockTransport(misp)))
    assert await a.lookup("198.51.100.1") == Verdict(True, 87, ["abuseipdb"])
    assert await m.lookup("198.51.100.1") == Verdict(False, 0, [])
    merged = await ThreatIntel([a, m]).lookup("198.51.100.1")
    assert merged == Verdict(True, 87, ["abuseipdb"])


class Flaky:
    name = "flaky"

    def __init__(self) -> None:
        self.calls = 0

    async def lookup(self, ip: str) -> Verdict | None:
        self.calls += 1
        raise httpx.ConnectError("down")


async def test_threat_intel_tolerates_failures_and_caches() -> None:
    flaky = Flaky()
    now = [0.0]
    ti = ThreatIntel([flaky], ttl_seconds=60, clock=lambda: now[0])
    assert await ti.lookup("198.51.100.2") is None
    assert await ti.lookup("198.51.100.2") is None and flaky.calls == 1  # cached
    now[0] = 61
    await ti.lookup("198.51.100.2")
    assert flaky.calls == 2


@pytest.mark.parametrize("detail", ["summary", "full"])
def test_reviewed_title(detail: str) -> None:
    ev = EVENT.model_copy(update={"event": "reviewed", "case": EVENT.case.model_copy(update={
        "review_status": "approved", "reviewed_by": "bob"})})
    assert "case approved by bob" in render(ev, detail).title
