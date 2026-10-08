# ADR-002: Deterministic core, LLM as ranker; human-in-the-loop for all actions

**Status:** Accepted · **Date:** 2026-06-30

**Context:** SOC decisions must be auditable (KVKK, ISO 27001, SOC2). LLM output is non-deterministic and the LLM input is attacker-influenceable (a log line can contain injected instructions).

**Alternatives considered:**
- LLM auto-executes response actions (isolate host, block IP) — rejected: unsafe, non-auditable, prompt-injection exposure.
- LLM as advisory layer only, deterministic core decides, human approves actions — **chosen.**

**Rationale:** Rule-based logic makes decisions; the LLM enriches, summarizes, and *suggests* with a confidence and rationale. Every response action requires human approval in the phases covered here. Mirrors the proven "deterministic core, AI as option-ranker" pattern.

**Risks / follow-ups:** Must enforce structured JSON output with schema validation; must log prompt + response + model + version + tokens for every call.
