from datetime import UTC, datetime, timedelta

from esm_common.contracts import Alert, Incident

from app.curate import build_masked_incident, is_private

T0 = datetime(2026, 10, 7, 18, 0, tzinfo=UTC)


async def fake_mask(incident_id: str, kind: str, values: list[str]) -> dict[str, str]:
    return {v: f"{kind}_{i:06x}" for i, v in enumerate(values)}


def incident() -> Incident:
    alerts = [
        Alert(id="a2", timestamp=T0 + timedelta(minutes=4), rule_id="esm-win-010",
              rule_name="PowerShell encoded command", severity="medium", host_name="PC-01",
              user_name="alice", source_ip="185.199.108.1", mitre_technique_ids=["T1027"],
              event_details={"process.command_line": "powershell -enc SECRET alice@corp.local"}),
        Alert(id="a1", timestamp=T0, rule_id="esm-win-001", rule_name="Office spawned shell",
              severity="high", host_name="PC-01", user_name="alice", source_ip="10.0.0.5",
              mitre_technique_ids=["T1059"]),
    ]
    return Incident(id="inc-1", created_at=T0, updated_at=T0 + timedelta(minutes=4), alerts=alerts,
                    alert_count=2, affected_hosts=["PC-01"], affected_users=["alice"],
                    source_ips=["10.0.0.5", "185.199.108.1"], mitre_techniques=["T1059", "T1027"],
                    risk_score=35)


async def test_masked_incident_has_no_plaintext() -> None:
    masked = await build_masked_incident(incident(), fake_mask)
    payload = masked.model_dump_json()
    for secret in ("PC-01", "alice", "10.0.0.5", "185.199.108.1", "SECRET", "corp.local"):
        assert secret not in payload, f"{secret} leaked into the LLM payload"
    assert masked.affected_hosts == ["host_000000"]
    assert masked.affected_users == ["user_000000"]


async def test_timeline_sorted_and_summary_aggregated() -> None:
    masked = await build_masked_incident(incident(), fake_mask)
    rules = [e.rule for e in masked.timeline]
    assert rules == ["Office spawned shell", "PowerShell encoded command"]
    assert masked.mitre_techniques == ["T1027", "T1059"]
    assert "2 alert(s) within 4 minute(s)" in masked.summary
    assert "source IPs: 2 (1 external)" in masked.summary
    assert "risk score 35/100" in masked.summary
    assert [ip.private for ip in masked.source_ips] == [True, False]


def test_is_private() -> None:
    assert is_private("192.168.1.1") and is_private("127.0.0.1")
    assert not is_private("8.8.8.8") and not is_private("not-an-ip")


class FakeTI:
    enabled = True

    def __init__(self) -> None:
        self.looked_up: list[str] = []

    async def lookup(self, ip: str):  # type: ignore[no-untyped-def]
        from esm_outbound.threatintel import Verdict

        self.looked_up.append(ip)
        return Verdict(malicious=True, score=90, sources=["abuseipdb"])


async def test_threat_intel_only_for_external_ips() -> None:
    ti = FakeTI()
    masked = await build_masked_incident(incident(), fake_mask, ti)  # type: ignore[arg-type]
    assert ti.looked_up == ["185.199.108.1"]  # 10.0.0.5 never leaves the platform
    external = [ip for ip in masked.source_ips if not ip.private]
    assert external[0].ti_malicious is True and external[0].ti_score == 90
    assert external[0].token.startswith("ip_")
    assert "threat intel: 1 of 1 external IP(s) flagged malicious" in masked.summary
    assert "185.199.108.1" not in masked.model_dump_json()
