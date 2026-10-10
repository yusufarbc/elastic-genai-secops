"""Build Kibana detection rules (NDJSON) from rules.yml.

Usage:
    python content/detection-rules/build.py           # write rules.ndjson
    python content/detection-rules/build.py --check   # fail if rules.ndjson is out of date

Requires PyYAML.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "rules.yml"
OUTPUT = HERE / "rules.ndjson"

RISK_SCORE = {"low": 21, "medium": 47, "high": 73, "critical": 99}
QUERY_INTERVAL, QUERY_FROM = "5m", "now-6m"

TACTICS = {
    "reconnaissance": ("TA0043", "Reconnaissance"),
    "initial-access": ("TA0001", "Initial Access"),
    "execution": ("TA0002", "Execution"),
    "persistence": ("TA0003", "Persistence"),
    "privilege-escalation": ("TA0004", "Privilege Escalation"),
    "defense-evasion": ("TA0005", "Defense Evasion"),
    "credential-access": ("TA0006", "Credential Access"),
    "lateral-movement": ("TA0008", "Lateral Movement"),
    "command-and-control": ("TA0011", "Command and Control"),
    "exfiltration": ("TA0010", "Exfiltration"),
}

# Parent technique names, needed when a rule references a sub-technique.
PARENT_TECHNIQUES = {
    "T1003": "OS Credential Dumping",
    "T1021": "Remote Services",
    "T1053": "Scheduled Task/Job",
    "T1059": "Command and Scripting Interpreter",
    "T1070": "Indicator Removal",
    "T1110": "Brute Force",
    "T1505": "Server Software Component",
    "T1543": "Create or Modify System Process",
    "T1546": "Event Triggered Execution",
    "T1547": "Boot or Logon Autostart Execution",
    "T1548": "Abuse Elevation Control Mechanism",
    "T1562": "Impair Defenses",
    "T1569": "System Services",
    "T1595": "Active Scanning",
}


def technique_url(technique_id: str) -> str:
    return "https://attack.mitre.org/techniques/" + technique_id.replace(".", "/") + "/"


def build_threat(mitre: list[dict]) -> list[dict]:
    """Group techniques by tactic in the shape Kibana expects."""
    by_tactic: dict[str, dict[str, dict]] = {}
    for entry in mitre:
        tactic, technique_id = entry["tactic"], entry["technique"]
        if tactic not in TACTICS:
            raise ValueError(f"unknown tactic {tactic!r}")
        name = entry["name"].split(": ", 1)[-1]
        techniques = by_tactic.setdefault(tactic, {})
        parent_id, _, sub = technique_id.partition(".")
        if sub:
            parent = techniques.setdefault(parent_id, {
                "id": parent_id,
                "name": PARENT_TECHNIQUES[parent_id],
                "reference": technique_url(parent_id),
                "subtechnique": [],
            })
            parent.setdefault("subtechnique", []).append(
                {"id": technique_id, "name": name, "reference": technique_url(technique_id)}
            )
        else:
            existing = techniques.setdefault(parent_id, {"id": parent_id, "reference": technique_url(parent_id)})
            existing["name"] = name
    threat = []
    for tactic, techniques in by_tactic.items():
        tactic_id, tactic_name = TACTICS[tactic]
        threat.append({
            "framework": "MITRE ATT&CK",
            "tactic": {
                "id": tactic_id,
                "name": tactic_name,
                "reference": f"https://attack.mitre.org/tactics/{tactic_id}/",
            },
            "technique": list(techniques.values()),
        })
    return threat


def window_minutes(window: str) -> int:
    match = re.fullmatch(r"(\d+)([mh])", window)
    if not match:
        raise ValueError(f"window must look like 10m or 1h, got {window!r}")
    value, unit = int(match.group(1)), match.group(2)
    return value * 60 if unit == "h" else value


def build_note(rule: dict) -> str:
    lines = ["## Triage and response", ""]
    lines += [f"{i}. {step}" for i, step in enumerate(rule.get("playbook", []), start=1)]
    return "\n".join(lines)


def build_rule(rule: dict) -> dict:
    severity = rule["severity"]
    tags = ["Elastic GenAI SecOps", f"Rule ID: {rule['id']}"]
    tags += sorted({f"MITRE: {m['technique']}" for m in rule.get("mitre", [])})
    out = {
        "rule_id": "esm-" + rule["id"].lower(),
        "name": f"[{rule['id']}] {rule['name']}",
        "description": rule["description"],
        "severity": severity,
        "risk_score": RISK_SCORE[severity],
        "language": "kuery",
        "query": " ".join(rule["query"].split()),
        "index": rule["index"],
        "enabled": rule.get("enabled", True),
        "interval": QUERY_INTERVAL,
        "from": QUERY_FROM,
        "max_signals": 100,
        "tags": tags,
        "threat": build_threat(rule.get("mitre", [])),
        "false_positives": rule.get("false_positives", []),
        "references": rule.get("references", []),
        "note": build_note(rule),
        "author": ["Elastic GenAI SecOps"],
        "license": "Apache-2.0",
        "version": rule.get("version", 1),
        "type": "query",
    }
    threshold = rule.get("threshold")
    if threshold:
        minutes = window_minutes(threshold["window"])
        out["type"] = "threshold"
        out["threshold"] = {"field": [threshold["field"]], "value": threshold["value"]}
        out["interval"] = f"{minutes}m"
        out["from"] = f"now-{minutes + 1}m"
    return out


def render() -> str:
    data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    rules = data["rules"]
    ids = [r["id"] for r in rules]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate rule ids: {sorted(duplicates)}")
    return "".join(json.dumps(build_rule(r), ensure_ascii=False, sort_keys=True) + "\n" for r in rules)


def main() -> int:
    content = render()
    if "--check" in sys.argv[1:]:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print("rules.ndjson is out of date; run: python content/detection-rules/build.py")
            return 1
        print(f"rules.ndjson is up to date ({content.count(chr(10))} rules)")
        return 0
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(HERE.parent.parent)} ({content.count(chr(10))} rules)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
