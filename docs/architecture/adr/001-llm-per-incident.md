# ADR-001: LLM is triggered per INCIDENT, never per alert or per log

**Status:** Accepted · **Date:** 2026-06-30

**Context:** The original idea was to send every alert (or every log) to the LLM at "first level" 24/7. At Fortune-500-scale log volumes this is economically and operationally unworkable.

**Alternatives considered:**
- Per-log LLM triage — rejected: astronomical cost, moves alert fatigue onto the LLM layer.
- Per-alert LLM triage — rejected: still 20–50x the request volume of incident-level, and the LLM sees fragments instead of the whole picture, producing lower-quality triage.
- Per-incident LLM triage — **chosen.**

**Rationale:** Aggregating related alerts into one incident before any LLM call cuts request count by 10–50x, gives the LLM full context (timeline + affected assets + triggered MITRE techniques) for better triage, and makes cost predictable. This single decision is the dominant cost lever — model choice is secondary.

**Risks / follow-ups:** Correlation/aggregation logic in `alert-gateway` must be solid; bad correlation either floods the LLM or merges unrelated events. Needs tuning and measurement.
