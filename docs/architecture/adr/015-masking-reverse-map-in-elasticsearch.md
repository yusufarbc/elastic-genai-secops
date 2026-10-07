# ADR-015: masking-service reverse-map stored in Elasticsearch (NOT in-memory)

**Status:** Accepted · **Date:** 2026-06-30

**Context:** The original `Masker` class stored the incident→token reverse-map in process memory. With a single replica this works, but GKE HPA can scale the service to multiple pods; each pod would then hold a disjoint subset of the maps, breaking unmask calls routed to a different replica.

**Alternatives considered:**
- Single replica forever (no HPA) — rejected: masking-service is on the critical path for both enrichment (mask) and case-service (unmask); a single pod is a single point of failure.
- Shared Redis / Memorystore — rejected: adds a third stateful system alongside Elasticsearch; more operational surface for no advantage given ES is already present.
- Elasticsearch (existing cluster) — **chosen.**

**Rationale:** ES is already the system of record. Adding one lightweight index (`esm-masking-maps`, ~100 bytes per incident) is trivial. Token generation is deterministic (`sha256(incident_id:kind:plaintext)`) so concurrent replicas compute the same token without coordination — upserts converge. Painless script + `retry_on_conflict=5` handles concurrent writes safely. Index uses `"enabled": false` on the map objects (stored, not indexed) to avoid dynamic-mapping issues.

**Implementation:** `ElasticsearchMasker` in `services/masking-service/app/masker/masker.py`. The original in-memory `Masker` class is retained for unit tests and local dev (no ES required). `main.py` uses `ElasticsearchMasker` in production.

**Risks / follow-ups:** Define a TTL / cleanup policy for the `esm-masking-maps` index (ILM or a periodic delete of maps older than the incident retention window).
