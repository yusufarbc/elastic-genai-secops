# ADR-013: Message bus: GCP Pub/Sub (NOT Kafka)

**Status:** Accepted · **Date:** 2026-06-30 · **Amended by:** [ADR-017](017-portable-message-bus.md)

**Context:** The Elastic-SecOps-Mastery pipeline requires an async queue between alert-gateway → enrichment → masking → llm-orchestrator → case-service. Two realistic options: GCP Pub/Sub (managed, no ops) and Apache Kafka (self-hosted or Confluent Cloud).

**Alternatives considered:**

- Apache Kafka (self-hosted) — rejected for MVP: adds another stateful cluster to operate alongside Elasticsearch. Two stateful clusters for a two-person team is over-engineering at this stage.
- Confluent Cloud (managed Kafka) — rejected: additional vendor + billing overhead; no advantage over Pub/Sub when already on GCP.
- GCP Pub/Sub — **chosen.**

**Rationale:** Pub/Sub is fully managed, integrates with Workload Identity (no broker credentials in pods), and its `at-least-once` delivery + `ack` semantics match the pipeline's requirements. Already on GCP (ADR-007) so no new vendor. For local development, the official `google-cloud-sdk` Pub/Sub emulator runs in docker-compose. The queue is defined behind an interface in each service so swapping to Kafka later requires only a new adapter, not business logic changes.

**Topic layout:**

- `esm.alerts` — detection-service → alert-gateway
- `esm.incidents` — alert-gateway → enrichment-service
- `esm.masked-incidents` — masking-service → llm-orchestrator
- `esm.triage-decisions` — llm-orchestrator → case-service
- `esm.dlq` — dead-letter for all topics

**Risks / follow-ups:** Pub/Sub ordering is per-message-key (ordering keys); use `incident_id` as the key for masking → llm → case pipeline to preserve causal order.
