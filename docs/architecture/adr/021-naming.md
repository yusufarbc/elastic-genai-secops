# ADR-021: Naming: Elastic GenAI SecOps and the `esm` prefix

**Status:** Accepted · **Date:** 2026-10-07 · **Amended:** 2026-10-10 (product renamed from Elastic-SecOps-Mastery)

**Context:** The source projects used the names Sentinel and Elastic-GenAI-SOC. "Sentinel" collides with Microsoft Sentinel and SentinelOne, which are frequently mentioned in detection content. The consolidated project was first called Elastic-SecOps-Mastery; when it was published, the repository was renamed to `elastic-genai-secops` to say what the project is: generative-AI-assisted security operations on the Elastic Stack.

**Decision:** The product is named **Elastic GenAI SecOps**; the repository, container image path (`ghcr.io/<owner>/elastic-genai-secops/<service>`) and Kubernetes `app.kubernetes.io/part-of` label use `elastic-genai-secops`. Technical identifiers keep the `esm` prefix:

- Kubernetes namespace `esm`, ConfigMap `esm-config`
- Bus topics `esm.alerts`, `esm.incidents`, `esm.masked-incidents`, `esm.triage-decisions`, `esm.dlq`
- Indices `esm-masking-maps`, `esm-cases-*`, `esm-llm-audit`
- Go module paths `esm/<service>`

**Rationale:** One consistent, collision-free name across code, infrastructure and documentation. The `esm` prefix stays because it names stored data (indices, roles, users) and wire contracts (subjects); renaming it would break existing deployments for no functional gain.
