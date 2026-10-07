# ADR-019: Deployment profiles and targets

**Status:** Accepted (implementation: Phase 3) · **Date:** 2026-10-07 · **Amends:** [ADR-007](007-gke-kubernetes-platform.md), [ADR-016](016-gke-autopilot.md)

**Context:** The repository consolidates a bare-metal Ubuntu ELK installer, an ECK quickstart and a GKE-oriented AI platform. Users range from a single SOC analyst with one VM to teams running Kubernetes.

**Decision:** Separate *what* is installed (profile) from *where* it runs (target).

| Profile | Components |
|---|---|
| `siem` | Elasticsearch, Kibana, Logstash, detection rules, source integrations |
| `ai-lite` | `siem` + masking-service, llm-orchestrator, mcp-server |
| `full` | All platform services + message bus + case-service + bff |

| Target | Location |
|---|---|
| Docker Compose | `deploy/compose/` (layered compose files) |
| Kubernetes (ECK) | `deploy/kubernetes/` (kustomize `base/` + `overlays/{lab,onprem,gke}`) |
| Bare metal (Ubuntu) | `deploy/baremetal/ubuntu/` |
| Hybrid | Any target pointed at an existing cluster through `ELASTIC_URL` |

GKE Autopilot (ADR-016) remains the reference cloud target as the `gke` overlay.

**Rationale:** Most users start with `siem` and add AI later. Keeping profiles independent of targets avoids maintaining one manifest set per combination.

**Risks / follow-ups:** Every profile × target combination that is documented must be exercised in CI or in a documented manual test.
