# ADR-003: Token & privacy minimization is achieved by context curation, NOT by RAG

**Status:** Accepted · **Date:** 2026-06-30

**Context:** The initial assumption was that RAG would reduce tokens sent to the LLM and improve privacy. RAG *adds* context to the prompt — it increases tokens. The real goals (fewer tokens, less sensitive data to the LLM) are met by other means.

**Alternatives considered:**
- Use RAG as the primary token/privacy reducer — rejected: RAG grows prompts; it is the wrong tool for reduction.
- Context curation (pre-aggregation, field selection, deterministic enrichment) + masking, with RAG reserved for org-specific knowledge only — **chosen.**

**Rationale:**
- **Request count** is reduced by tuning + correlation + incident aggregation (ADR-001).
- **Tokens per request** are reduced by sending curated, aggregated features (e.g. "500 failed logins from 3 IPs in 10 min on host X") instead of raw log lines, and by selecting only the handful of fields needed for triage.
- **Deterministic enrichment** (GeoIP, threat-intel match, asset criticality) is resolved in code and passed as short strings, not handed to the LLM as raw data to reason over.
- **RAG** is used only for organization-specific knowledge the model does not have (internal playbooks, past incident dispositions, asset context) — never for general MITRE/CVE knowledge the model already holds.

**Risks / follow-ups:** Curation logic must not strip detail needed for correct triage; balance is empirical and needs tuning.
