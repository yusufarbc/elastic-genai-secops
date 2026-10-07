# ADR-018: Multiple LLM providers behind the provider interface

**Status:** Accepted (implementation: Phase 4) · **Date:** 2026-10-07 · **Amends:** [ADR-005](005-llm-model-gemini-2-5-flash.md), [ADR-006](006-llm-via-vertex-ai.md)

**Context:** ADR-005/006 chose Gemini 2.5 Flash on Vertex AI as the default. On-prem and air-gapped users cannot send data to a cloud LLM, and other users already have contracts with other vendors.

**Decision:** `llm-orchestrator` ships these providers, selected with `LLM_PROVIDER`:

| Provider | Use case |
|---|---|
| `mock` | CI and local development (default) |
| `ollama` | Local or air-gapped inference |
| `openai-compatible` | OpenAI, Azure OpenAI, vLLM, LM Studio and other OpenAI-API servers |
| `anthropic` | Claude models |
| `vertex` | Gemini on GCP Vertex AI (the ADR-005/006 setup) |

The rules from ADR-001 to ADR-004 apply to every provider: one call per incident, masked input only, JSON output validated against the triage schema, and an audit record for every call.

**Rationale:** The provider interface (`services/llm-orchestrator/app/provider/base.py`) already isolates vendor SDKs, so adding providers costs little and makes the platform usable in every deployment target.

**Risks / follow-ups:** Small local models follow the JSON schema less reliably. Keep the repair/reject path and measure the schema-failure rate per provider.
