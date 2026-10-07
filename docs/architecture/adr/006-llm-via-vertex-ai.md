# ADR-006: Run the LLM via GCP Vertex AI (NOT Google AI Studio)

**Status:** Accepted · **Date:** 2026-06-30 · **Amended by:** [ADR-018](018-multiple-llm-providers.md)

**Context:** The whole platform runs on GCP/GKE. The LLM can be called via Vertex AI (enterprise surface) or Google AI Studio / Gemini Developer API (dev/prototype surface). These are different products with different data-handling terms.

**Alternatives considered:**
- Google AI Studio / Gemini Developer API — rejected for production: free tier may use content to improve Google's products; weaker enterprise governance.
- Vertex AI — **chosen.**

**Rationale:** Vertex AI keeps inference inside the GCP org boundary, allows region pinning, integrates with Workload Identity (no API-key files for GKE services), VPC Service Controls, and unified billing/observability with Pub/Sub, GKE, and Elasticsearch. Directly supports the privacy posture in ADR-004. `llm-orchestrator` implements the Vertex AI SDK behind the swappable interface from ADR-005.

**Risks / follow-ups:** Confirm region and data-processing terms contractually. Must use paid tier — never free tier — because the system processes log data.
