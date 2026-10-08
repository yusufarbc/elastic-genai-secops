# ADR-014: Elastic Basic-tier feature availability (initial research)

**Status:** Accepted · **Date:** 2026-06-30

**Context:** Design rule 6 (ROADMAP.md): verify every Elastic feature against the free/Basic tier before depending on it.

**Findings (as of Elasticsearch 8.x):**

| Feature | Tier | Decision |
| --- | --- | --- |
| SIEM detection rules (KQL/EQL/threshold) | **Free/Basic** | ✅ Use — core detection engine |
| Kibana Security app (alerts UI, timeline) | **Free/Basic** | ✅ Use — analyst exploration UI |
| Fleet / Elastic Agent management | **Free/Basic** | ✅ Use — agent management |
| ILM (Index Lifecycle Management) | **Free/Basic** | ✅ Use — 14-day hot tier (ADR-009) |
| GCS snapshot repository | **Free/Basic** | ✅ Use — archive to GCS (ADR-010) |
| `dense_vector` field + kNN search | **Free/Basic** | ✅ Use — RAG vector store fallback |
| ELSER (Elastic Learned Sparse Encoder) | **Platinum** | ❌ Blocked — use `dense_vector` + self-hosted embeddings instead |
| Entity risk scoring | **Platinum** | ❌ Blocked — implement risk scoring in `alert-gateway` as code |
| ML anomaly detection jobs | **Platinum** | ❌ Blocked — use rule-based detection in Basic |
| Searchable snapshots | **Enterprise** | ❌ Blocked — see ADR-010; use raw GCS snapshot + manual restore |
| Cross-cluster replication | **Platinum** | ❌ Not needed at MVP |

**Risks / follow-ups:** The missing risk-scoring feature (normally Platinum) is compensated by deterministic risk scoring in `alert-gateway` using rule severity + CVSS + asset criticality. This is documented in the service design.
