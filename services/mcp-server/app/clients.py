"""HTTP clients for the platform APIs the MCP server reads from."""

from __future__ import annotations

import os
from typing import Any

import httpx


class CaseAPI:
    """Reads cases through bff (the analyst API); never touches the case store directly."""

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=15)

    async def list(self, review_status: str, size: int) -> list[dict[str, Any]]:
        params = {"size": str(size)}
        if review_status:
            params["review_status"] = review_status
        resp = await self._client.get("/cases", params=params)
        resp.raise_for_status()
        return resp.json()["cases"]

    async def get(self, case_id: str) -> dict[str, Any] | None:
        resp = await self._client.get(f"/cases/{case_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


class Masking:
    """Gets the same tokens masking-service gave llm-orchestrator for an incident."""

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=15)

    async def tokens(self, incident_id: str, items: list[tuple[str, str]]) -> dict[str, str]:
        """Return {plaintext: token} for (kind, plaintext) items."""
        items = [(k, v) for k, v in dict.fromkeys(items) if v]
        if not items:
            return {}
        resp = await self._client.post("/mask-batch", json={
            "incident_id": incident_id,
            "items": [{"kind": k, "plaintext": v} for k, v in items],
        })
        resp.raise_for_status()
        return {v: t for (_, v), t in zip(items, resp.json()["tokens"], strict=True)}


class Elasticsearch:
    """Minimal search client for alert statistics and allow-listed hunts."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @classmethod
    def from_env(cls) -> Elasticsearch:
        ca = os.getenv("ELASTIC_CA_CERTS") or True
        return cls(httpx.AsyncClient(
            base_url=os.getenv("ELASTIC_URL", "https://localhost:9200").rstrip("/"),
            auth=(os.getenv("ELASTIC_USER", "esm_platform"), os.getenv("ELASTIC_PASSWORD", "")),
            verify=ca, timeout=30,
        ))

    async def search(self, index: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"/{index}/_search", params={"ignore_unavailable": "true", "allow_no_indices": "true"},
            json=body)
        resp.raise_for_status()
        return resp.json()
