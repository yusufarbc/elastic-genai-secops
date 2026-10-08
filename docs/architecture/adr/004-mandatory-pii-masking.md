# ADR-004: Mandatory PII masking / pseudonymization before the LLM

**Status:** Accepted · **Date:** 2026-06-30

**Context:** Privacy concern about company logs reaching a US-origin LLM API, plus KVKK cross-border transfer exposure, plus prompt-injection surface reduction.

**Alternatives considered:**
- Send raw identifiers (usernames, IPs, hostnames, emails) to the LLM — rejected: privacy, compliance, and injection risks.
- Reversible pseudonymization before the LLM, un-mask after — **chosen.**

**Rationale:** Identifiers are mapped to stable tokens (`user_a1`, `host_x3`, `ip_7`) before anything reaches `llm-orchestrator`. A reverse-map is held per incident by a single component (`masking-service`). The LLM reasons over masked data; `case-service` un-masks the decision. This is a compliance control, not an optimization. Note: running the LLM via Vertex AI in-region (ADR-006) further reduces transfer exposure; masking is defense-in-depth on top of that.

**Risks / follow-ups:** Only `masking-service` may hold plaintext reverse-maps. Reverse-map lifecycle (TTL, deletion) must be defined. Legal review of cross-border transfer still recommended even with masking + in-region inference.
