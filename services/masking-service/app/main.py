"""masking-service — the ONLY service that holds plaintext PII reverse-maps.

HTTP API:
  POST   /mask              one identifier            (enrichment-service)
  POST   /mask-batch        many identifiers          (enrichment-service)
  POST   /unmask            one token                 (case-service)
  GET    /map/{incident_id} token -> plaintext map    (case-service, used transiently)
  DELETE /map/{incident_id} drop an incident's map
Reverse-maps are persisted in Elasticsearch (ADR-015) so replicas share state.
Only case-service and enrichment-service should be able to reach this API (network policy).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, Response

from app.masker import ElasticsearchMasker
from app.models import (
    MaskBatchRequest,
    MaskBatchResponse,
    MaskRequest,
    MaskResponse,
    ReverseMapResponse,
    UnmaskRequest,
    UnmaskResponse,
)

logger = structlog.get_logger(__name__)


def _build_es() -> AsyncElasticsearch:
    kwargs: dict = {
        "hosts": [os.getenv("ELASTIC_URL", "https://localhost:9200")],
        "basic_auth": (os.getenv("ELASTIC_USER", "elastic"), os.getenv("ELASTIC_PASSWORD", "")),
    }
    if ca := os.getenv("ELASTIC_CA_CERTS"):
        kwargs["ca_certs"] = ca
    return AsyncElasticsearch(**kwargs)


_es = _build_es()
_masker = ElasticsearchMasker(_es)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    while True:
        try:
            await _masker.ensure_index()
            break
        except Exception as exc:  # ES not reachable yet
            logger.warning("waiting for Elasticsearch", error=str(exc))
            await asyncio.sleep(5)
    logger.info("masking-service started")
    yield
    await _es.close()


app = FastAPI(title="masking-service", version="0.2.0", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/mask", response_model=MaskResponse)
async def mask(req: MaskRequest) -> MaskResponse:
    return MaskResponse(token=await _masker.mask(req.incident_id, req.kind, req.plaintext))


@app.post("/mask-batch", response_model=MaskBatchResponse)
async def mask_batch(req: MaskBatchRequest) -> MaskBatchResponse:
    tokens = [await _masker.mask(req.incident_id, i.kind, i.plaintext) for i in req.items]
    return MaskBatchResponse(tokens=tokens)


@app.post("/unmask", response_model=UnmaskResponse)
async def unmask(req: UnmaskRequest) -> UnmaskResponse:
    return UnmaskResponse(plaintext=await _masker.unmask(req.incident_id, req.token))


@app.get("/map/{incident_id}", response_model=ReverseMapResponse)
async def get_map(incident_id: str) -> ReverseMapResponse:
    return ReverseMapResponse(incident_id=incident_id,
                              token_to_plain=await _masker.get_reverse_map(incident_id))


@app.delete("/map/{incident_id}", status_code=204)
async def delete_map(incident_id: str) -> Response:
    await _masker.delete_map(incident_id)
    logger.info("reverse-map deleted", incident_id=incident_id)
    return Response(status_code=204)


if __name__ == "__main__":
    from esm_common.logging import configure

    configure("masking-service")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")), log_config=None)
