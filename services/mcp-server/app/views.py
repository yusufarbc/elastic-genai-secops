"""Masked views of cases for MCP clients.

An MCP client is an LLM, so it gets the same pseudonymized view llm-orchestrator got
(design rule 3, ROADMAP.md): hosts, users and IPs are replaced with the incident's tokens, also inside
free text such as the summary. Analyst notes and reviewer names are not exposed.
"""

from __future__ import annotations

from typing import Any

from app.clients import Masking

SUMMARY_FIELDS = ("id", "created_at", "severity", "risk_score", "alert_count", "triage_status",
                  "review_status", "mitre_techniques", "summary")
DETAIL_FIELDS = SUMMARY_FIELDS + ("incident_summary", "recommended_actions", "rationale",
                                  "confidence", "false_positive_likelihood", "affected_hosts",
                                  "affected_users", "source_ips", "timeline", "model_id")


def _identifiers(case: dict[str, Any]) -> list[tuple[str, str]]:
    items = [("host", h) for h in case.get("affected_hosts") or []]
    items += [("user", u) for u in case.get("affected_users") or []]
    items += [("ip", ip) for ip in case.get("source_ips") or []]
    for e in case.get("timeline") or []:
        items += [("host", e.get("host", "")), ("user", e.get("user", ""))]
    return items


def _replace(value: Any, tokens: dict[str, str], ordered: list[str]) -> Any:
    if isinstance(value, str):
        if value in tokens:
            return tokens[value]
        for plain in ordered:  # longest first, so "host-10" is not hit by "host-1"
            value = value.replace(plain, tokens[plain])
        return value
    if isinstance(value, list):
        return [_replace(v, tokens, ordered) for v in value]
    if isinstance(value, dict):
        return {k: _replace(v, tokens, ordered) for k, v in value.items()}
    return value


async def mask_case(case: dict[str, Any], masking: Masking, *, detail: bool) -> dict[str, Any]:
    fields = DETAIL_FIELDS if detail else SUMMARY_FIELDS
    view = {k: case[k] for k in fields if k in case}
    tokens = await masking.tokens(case.get("incident_id") or case["id"], _identifiers(case))
    ordered = sorted(tokens, key=len, reverse=True)
    return _replace(view, tokens, ordered)
