# ADR-017: Portable message bus: NATS JetStream on-prem, Pub/Sub on GCP

**Status:** Accepted (implementation: Phase 4) · **Date:** 2026-10-07 · **Amends:** [ADR-013](013-message-bus-pubsub.md)

**Context:** The consolidated platform must run on Docker Compose, on-prem Kubernetes, bare metal and GKE. ADR-013 tied the pipeline to GCP Pub/Sub, so every non-GCP deployment would need either a GCP project or the Pub/Sub emulator, which is not supported for production use.

**Alternatives considered:**

- Keep Pub/Sub everywhere: rejected; it makes on-prem and air-gapped installs depend on GCP.
- Apache Kafka: rejected for the same reason as in ADR-013 (a second heavy stateful cluster).
- Redis Streams: viable, but consumer-group, retry and dead-letter semantics have to be built by hand.
- NATS JetStream for on-prem and local, Pub/Sub on GCP, behind one interface: **chosen.**

**Decision:** Every service talks to a `Bus` interface (`libs/go-common/bus`, `libs/py-common/esm_common/bus`). The adapter is selected with `BUS_BACKEND=nats|pubsub`. Topic names from ADR-013 stay the same (`esm.alerts`, `esm.incidents`, ...) and map to JetStream subjects or Pub/Sub topics.

**Rationale:** NATS is a single small binary with at-least-once delivery, ack, redelivery and stream persistence, and it runs equally well in Compose, on Kubernetes and as a systemd service. Pub/Sub remains the managed option on GCP with Workload Identity.

**Risks / follow-ups:** Contract tests must run against both adapters. Keep ordering by `incident_id` (Pub/Sub ordering key, JetStream subject token).
