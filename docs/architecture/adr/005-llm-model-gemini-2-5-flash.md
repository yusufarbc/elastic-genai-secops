# ADR-005: LLM model: Gemini 2.5 Flash, behind a swappable provider interface

**Status:** Accepted · **Date:** 2026-06-30 · **Amended by:** [ADR-018](018-multiple-llm-providers.md)

**Context:** Requirement: US-origin commercial model, billed API, system runs entirely in English. Candidates compared: Claude Haiku 4.5 vs Gemini 2.5 Flash vs Gemini 3.5 Flash vs Gemini 3.1 Flash-Lite.

**Pricing compared (USD per million tokens, standard; verify before budgeting — prices change fast):**
| Model | Input | Output |
|---|---|---|
| Claude Haiku 4.5 | $1.00 | $5.00 |
| Gemini 2.5 Flash | $0.30 | $2.50 |
| Gemini 3.5 Flash | $1.50 | $9.00 |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 |

**Estimated monthly cost** (assuming correct incident-level architecture: ~500 incidents/day, ~3,000 input + ~800 output tokens each): Gemini 2.5 Flash ≈ $44/mo; Haiku 4.5 ≈ $105/mo; Gemini 3.5 Flash ≈ $176/mo. All negligible at this scale — **architecture, not model, determines cost.**

**Alternatives considered:**
- Claude Haiku 4.5 — strong instruction-following, structured-output discipline, injection resistance; kept as the documented fallback for A/B testing and for escalated incidents.
- Gemini 3.5 Flash — newer default but more expensive than Haiku; not chosen for cost reasons.
- Gemini 2.5 Flash — **chosen** as default: US-origin, cheapest viable, 1M context, and consolidates onto GCP (ADR-006).

**Rationale:** Triage (summarization, MITRE-mapping interpretation, structured JSON, prioritization) is squarely in the Flash/Haiku capability class. Gemini 2.5 Flash chosen for cost + GCP consolidation. The provider/model MUST sit behind an interface so Haiku (or any model) can be swapped via one adapter without touching business logic — preserves the "no vendor lock-in / digital sovereignty" principle.

**Risks / follow-ups:**
- Run a one-week A/B of Gemini 2.5 Flash vs Haiku on real incidents; measure MITRE-mapping accuracy, false-positive capture, and JSON conformance. Let quality decide, since cost is negligible either way.
- Implement tiered routing: default to Flash; escalate complex/high-stakes incidents to a stronger model.
- Model IDs change/deprecate fast — keep the model ID in config, never hard-coded.
