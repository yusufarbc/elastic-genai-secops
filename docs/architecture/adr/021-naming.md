# ADR-021: Naming: Elastic-SecOps-Mastery and the `esm` prefix

**Status:** Accepted · **Date:** 2026-10-07

**Context:** The source projects used the names Sentinel and Elastic-GenAI-SOC. "Sentinel" collides with Microsoft Sentinel and SentinelOne, which are frequently mentioned in detection content.

**Decision:** The product and repository are named **Elastic-SecOps-Mastery**. Technical identifiers use the `esm` prefix:

- Kubernetes namespace `esm`, ConfigMap `esm-config`
- Bus topics `esm.alerts`, `esm.incidents`, `esm.masked-incidents`, `esm.triage-decisions`, `esm.dlq`
- Indices `esm-masking-maps`, `esm-cases-*`, `esm-llm-audit`
- Go module paths `esm/<service>`

**Rationale:** One consistent, collision-free name across code, infrastructure and documentation.
