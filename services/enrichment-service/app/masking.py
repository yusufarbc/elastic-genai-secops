"""Client for masking-service, the only holder of reverse maps (ADR-004, ADR-015)."""

from __future__ import annotations

import httpx


class MaskingClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=15)

    async def mask(self, incident_id: str, kind: str, values: list[str]) -> dict[str, str]:
        """Return {plaintext: token} for values within one incident."""
        resp = await self._client.post("/mask-batch", json={
            "incident_id": incident_id,
            "items": [{"kind": kind, "plaintext": v} for v in values],
        })
        resp.raise_for_status()
        tokens = resp.json()["tokens"]
        if len(tokens) != len(values):
            raise ValueError("masking-service returned a different number of tokens")
        return dict(zip(values, tokens, strict=True))

    async def close(self) -> None:
        await self._client.aclose()
