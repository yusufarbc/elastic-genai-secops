"""Allow-listed hunting queries (content/hunting/hunts.yml)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Fields that identify people or machines must never be used for grouping (results go to an LLM).
_FORBIDDEN_GROUP_PARTS = ("host", "user", "computer", "email", "account", "sid")


def _identifies_entity(field: str) -> bool:
    f = field.lower()
    return f.endswith(".ip") or f == "ip" or any(part in f for part in _FORBIDDEN_GROUP_PARTS)


@dataclass(frozen=True)
class Hunt:
    id: str
    title: str
    description: str
    index: str
    query: str
    group_by: tuple[str, ...]
    mitre: tuple[str, ...]


def load_hunts(path: Path) -> dict[str, Hunt]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    hunts: dict[str, Hunt] = {}
    for h in data["hunts"]:
        group_by = tuple(h.get("group_by") or ())
        if len(group_by) > 3:
            raise ValueError(f"hunt {h['id']}: at most 3 group_by fields")
        for field in group_by:
            if _identifies_entity(field):
                raise ValueError(f"hunt {h['id']}: group_by field {field} identifies an entity")
        hunts[h["id"]] = Hunt(id=h["id"], title=h["title"], description=h["description"],
                              index=h["index"], query=h["query"], group_by=group_by,
                              mitre=tuple(h.get("mitre") or ()))
    return hunts


def build_query(hunt: Hunt, hours: int, top: int) -> dict[str, Any]:
    return {
        "size": 0,
        "track_total_hits": True,
        "query": {"bool": {"filter": [
            {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
            {"query_string": {"query": hunt.query, "analyze_wildcard": True}},
        ]}},
        "aggs": {f: {"terms": {"field": f, "size": top}} for f in hunt.group_by},
    }


def summarize(hunt: Hunt, hours: int, result: dict[str, Any]) -> dict[str, Any]:
    aggs = result.get("aggregations") or {}
    return {
        "hunt": hunt.id,
        "title": hunt.title,
        "window_hours": hours,
        "mitre": list(hunt.mitre),
        "total_hits": result.get("hits", {}).get("total", {}).get("value", 0),
        "top_values": {f: [{"value": b["key"], "count": b["doc_count"]}
                           for b in aggs.get(f, {}).get("buckets", [])] for f in hunt.group_by},
    }
