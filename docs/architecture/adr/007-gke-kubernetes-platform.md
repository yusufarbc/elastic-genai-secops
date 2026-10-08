# ADR-007: GKE + Kubernetes for the platform; stateless services autoscale

**Status:** Accepted · **Date:** 2026-06-30 · **Amended by:** [ADR-019](019-deployment-profiles-and-targets.md)

**Context:** Containerized microservice architecture with autoscaling, deployed on a major cloud. GKE chosen for native Kubernetes.

**Alternatives considered:** AWS / Azure — viable, but GCP chosen for native K8s + consolidation with Vertex AI (ADR-006) and GCS archival (ADR-009).

**Rationale:** The custom microservices (alert-gateway, enrichment, masking, llm-orchestrator, case-service, bff, response) are **stateless** — pods are cattle, not pets; HPA scales them trivially because they hold no persistent data. Kubernetes is ideal for this. Elasticsearch is the one stateful exception, handled separately (ADR-008).

**Risks / follow-ups:** Keep state out of the stateless services; Elasticsearch is the system of record for telemetry.
