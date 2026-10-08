"""Turn an incident into the curated, masked payload the LLM sees (CLAUDE.md section 5).

Only aggregated facts and pseudonymized identifiers leave this module. Free-text event fields
(command lines, messages) are deliberately not forwarded because they can carry PII and
attacker-controlled text.
"""

from __future__ import annotations

import ipaddress
from collections import Counter
from collections.abc import Awaitable, Callable

from esm_common.contracts import Incident, MaskedIncident, MaskedIP, TimelineEntry
from esm_outbound.threatintel import ThreatIntel

# mask(incident_id, kind, values) -> {plaintext: token}
MaskFn = Callable[[str, str, list[str]], Awaitable[dict[str, str]]]
MAX_TI_LOOKUPS = 20  # external IPs looked up per incident

MAX_TIMELINE = 50
MAX_RULES_IN_SUMMARY = 5


def _unique(values: list[str | None]) -> list[str]:
    return sorted({v for v in values if v})


def is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local


async def _threat_intel(ips: list[str], ti: ThreatIntel | None) -> dict[str, MaskedIP]:
    """Verdicts for external addresses only; internal addresses never leave the platform."""
    if ti is None or not ti.enabled:
        return {}
    out: dict[str, MaskedIP] = {}
    for ip in [i for i in ips if not is_private(i)][:MAX_TI_LOOKUPS]:
        verdict = await ti.lookup(ip)
        if verdict is not None:
            out[ip] = MaskedIP(token="", ti_malicious=verdict.malicious, ti_score=verdict.score,
                               ti_sources=verdict.sources or None)
    return out


async def build_masked_incident(incident: Incident, mask: MaskFn,
                                ti: ThreatIntel | None = None) -> MaskedIncident:
    hosts = _unique([*(incident.affected_hosts or []), *(a.host_name for a in incident.alerts)])
    users = _unique([*(incident.affected_users or []), *(a.user_name for a in incident.alerts)])
    ips = _unique([*(incident.source_ips or []), *(a.source_ip for a in incident.alerts)])

    host_tok = await mask(incident.id, "host", hosts) if hosts else {}
    user_tok = await mask(incident.id, "user", users) if users else {}
    ip_tok = await mask(incident.id, "ip", ips) if ips else {}
    verdicts = await _threat_intel(ips, ti)

    alerts = sorted(incident.alerts, key=lambda a: a.timestamp)
    timeline = [
        TimelineEntry(
            timestamp=a.timestamp,
            rule=a.rule_name or a.rule_id,
            severity=a.severity,
            host=host_tok.get(a.host_name, ""),
            user=user_tok.get(a.user_name, ""),
        )
        for a in alerts[:MAX_TIMELINE]
    ]
    techniques = _unique([*(incident.mitre_techniques or []),
                          *(t for a in alerts for t in (a.mitre_technique_ids or []))])

    masked = MaskedIncident(
        incident_id=incident.id,
        created_at=incident.created_at,
        summary="",
        affected_hosts=[host_tok[h] for h in hosts],
        affected_users=[user_tok[u] for u in users],
        source_ips=[
            verdicts[ip].model_copy(update={"token": ip_tok[ip], "private": False})
            if ip in verdicts else MaskedIP(token=ip_tok[ip], private=is_private(ip))
            for ip in ips
        ],
        timeline=timeline,
        mitre_techniques=techniques,
        risk_score=incident.risk_score,
        alert_count=incident.alert_count,
    )
    masked.summary = summarize(masked, Counter(a.rule_name or a.rule_id for a in alerts),
                               first=alerts[0].timestamp if alerts else incident.created_at,
                               last=alerts[-1].timestamp if alerts else incident.updated_at)
    return masked


def summarize(m: MaskedIncident, rules: Counter[str], first, last) -> str:  # type: ignore[no-untyped-def]
    """Deterministic, pre-aggregated summary built only from masked values."""
    minutes = max(1, round((last - first).total_seconds() / 60))
    top = ", ".join(f"{name} x{count}" for name, count in rules.most_common(MAX_RULES_IN_SUMMARY))
    external = sum(1 for ip in m.source_ips if not ip.private)
    parts = [
        f"{m.alert_count} alert(s) within {minutes} minute(s)",
        f"hosts: {', '.join(m.affected_hosts) or 'none'}",
        f"users: {', '.join(m.affected_users) or 'none'}",
        f"source IPs: {len(m.source_ips)} ({external} external)",
        f"rules: {top or 'unknown'}",
        f"MITRE: {', '.join(m.mitre_techniques) or 'none'}",
        f"risk score {m.risk_score}/100",
    ]
    checked = [ip for ip in m.source_ips if ip.ti_malicious is not None]
    if checked:
        flagged = sum(1 for ip in checked if ip.ti_malicious)
        parts.insert(
            4, f"threat intel: {flagged} of {len(checked)} external IP(s) flagged malicious")
    return "; ".join(parts) + "."
