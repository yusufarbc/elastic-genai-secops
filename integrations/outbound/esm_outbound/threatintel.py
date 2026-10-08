"""Threat-intel lookups for external IP addresses: AbuseIPDB and MISP.

Used by enrichment-service so the LLM receives a deterministic verdict ("flagged by threat
intel") instead of having to guess (CLAUDE.md section 5). Only public addresses are looked up;
lookup failures never block an incident.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Verdict:
    malicious: bool
    score: int = 0  # 0-100
    sources: list[str] = field(default_factory=list)


class ThreatIntelSource(Protocol):
    name: str

    async def lookup(self, ip: str) -> Verdict | None: ...


class AbuseIPDB:
    name = "abuseipdb"

    def __init__(self, api_key: str, client: httpx.AsyncClient, min_score: int = 50,
                 base_url: str = "https://api.abuseipdb.com") -> None:
        self._key, self._client, self._min = api_key, client, min_score
        self._url = base_url.rstrip("/")

    async def lookup(self, ip: str) -> Verdict | None:
        resp = await self._client.get(f"{self._url}/api/v2/check",
                                      params={"ipAddress": ip, "maxAgeInDays": "90"},
                                      headers={"Key": self._key, "Accept": "application/json"})
        resp.raise_for_status()
        score = int(resp.json()["data"].get("abuseConfidenceScore", 0))
        return Verdict(malicious=score >= self._min, score=score,
                       sources=[self.name] if score >= self._min else [])


class MISP:
    name = "misp"

    def __init__(self, url: str, api_key: str, client: httpx.AsyncClient) -> None:
        self._url, self._key, self._client = url.rstrip("/"), api_key, client

    async def lookup(self, ip: str) -> Verdict | None:
        resp = await self._client.post(
            f"{self._url}/attributes/restSearch",
            headers={"Authorization": self._key, "Accept": "application/json"},
            json={"returnFormat": "json", "value": ip, "type": ["ip-src", "ip-dst"],
                  "to_ids": True, "limit": 1},
        )
        resp.raise_for_status()
        hit = bool(resp.json().get("response", {}).get("Attribute"))
        return Verdict(malicious=hit, score=100 if hit else 0, sources=[self.name] if hit else [])


class ThreatIntel:
    """Queries every configured source, merges verdicts and caches them."""

    def __init__(self, sources: list[ThreatIntelSource], ttl_seconds: float = 3600,
                 max_entries: int = 10_000, clock=time.monotonic) -> None:  # type: ignore[no-untyped-def]
        self._sources, self._ttl, self._max, self._clock = sources, ttl_seconds, max_entries, clock
        self._cache: dict[str, tuple[float, Verdict | None]] = {}

    @property
    def enabled(self) -> bool:
        return bool(self._sources)

    async def lookup(self, ip: str) -> Verdict | None:
        now = self._clock()
        cached = self._cache.get(ip)
        if cached and now - cached[0] < self._ttl:
            return cached[1]
        verdicts: list[Verdict] = []
        for source in self._sources:
            try:
                v = await source.lookup(ip)
            except Exception as exc:  # a TI outage must not block incidents
                logger.warning("threat intel lookup failed", source=source.name, error=str(exc))
                continue
            if v is not None:
                verdicts.append(v)
        merged = None
        if verdicts:
            merged = Verdict(malicious=any(v.malicious for v in verdicts),
                             score=max(v.score for v in verdicts),
                             sources=sorted({s for v in verdicts for s in v.sources}))
        if len(self._cache) >= self._max:
            self._cache.clear()
        self._cache[ip] = (now, merged)
        return merged
