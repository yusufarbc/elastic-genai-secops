"""Turn a case event into text for humans.

Two detail levels, because notifications and tickets often go to third-party SaaS:
  summary  severity, risk, counts, rule names, MITRE techniques and a link - no hosts, users,
           IPs or free text (the LLM summary mentions hosts and users)
  full     adds affected entities, the triage summary and the recommended actions
"""

from __future__ import annotations

from dataclasses import dataclass, field

from esm_common.contracts import CaseEvent

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class Message:
    title: str
    facts: list[tuple[str, str]]
    sections: list[tuple[str, list[str]]] = field(default_factory=list)
    link: str = ""

    def markdown(self) -> str:
        lines = [f"**{self.title}**", ""]
        lines += [f"- **{k}:** {v}" for k, v in self.facts]
        for heading, items in self.sections:
            lines += ["", f"**{heading}**"] + [f"- {i}" for i in items]
        if self.link:
            lines += ["", f"[Open case]({self.link})"]
        return "\n".join(lines)

    def plain(self) -> str:
        lines = [self.title, ""] + [f"{k}: {v}" for k, v in self.facts]
        for heading, items in self.sections:
            lines += ["", heading] + [f"  - {i}" for i in items]
        if self.link:
            lines += ["", f"Case: {self.link}"]
        return "\n".join(lines)


def rule_names(event: CaseEvent) -> list[str]:
    names = [e.rule for e in event.case.timeline or [] if e.rule]
    return list(dict.fromkeys(names))


def render(event: CaseEvent, detail: str = "summary", case_url: str = "") -> Message:
    c = event.case
    rules = rule_names(event)
    if event.event == "reviewed":
        what = f"case {c.review_status} by {c.reviewed_by or 'an analyst'}"
    else:
        what = "new case awaiting review"
    title = f"[ESM] {c.severity.upper()} {what}: {rules[0] if rules else c.id}"

    facts = [
        ("Case", c.id),
        ("Severity", c.severity),
        ("Risk score", f"{c.risk_score}/100"),
        ("Alerts", str(c.alert_count)),
        ("Triage", c.triage_status or "unknown"),
        ("Review", c.review_status),
        ("MITRE", ", ".join(c.mitre_techniques or []) or "none"),
    ]
    sections: list[tuple[str, list[str]]] = [("Rules", rules[:10])] if rules else []
    if detail == "full":
        facts += [
            ("Hosts", ", ".join(c.affected_hosts or []) or "none"),
            ("Users", ", ".join(c.affected_users or []) or "none"),
            ("Source IPs", ", ".join(c.source_ips or []) or "none"),
        ]
        if c.summary:
            sections.append(("Triage summary (LLM suggestion)", [c.summary]))
        if c.recommended_actions:
            sections.append(("Suggested actions (for analyst review)", c.recommended_actions))
        if event.event == "reviewed" and c.analyst_notes:
            sections.append(("Analyst notes", [c.analyst_notes]))
    link = f"{case_url.rstrip('/')}/{c.id}" if case_url else ""
    return Message(title=title, facts=facts, sections=sections, link=link)


def meets(severity: str, minimum: str) -> bool:
    return SEVERITY_ORDER.get(severity, 0) >= SEVERITY_ORDER.get(minimum, 0)
