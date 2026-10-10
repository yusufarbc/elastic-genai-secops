# ADR-025: Reverse-map lifecycle: delete after review, TTL as a backstop

**Status:** Accepted · **Date:** 2026-10-10 · Resolves the lifecycle follow-up in ADR-004

**Context:** `masking-service` keeps one reverse map per incident in `esm-masking-maps` (ADR-015).
The maps are the only plaintext ↔ token mapping, so they should live no longer than needed. They had
no expiry, and `mcp-server` called `/mask-batch` to get display tokens, which wrote plaintext back
into a map every time a case was viewed.

**Decision:**

- `case-service` deletes an incident's map (`DELETE /map/{id}`) after the analyst review is stored.
  The case already holds the unmasked identifiers; a failed delete is logged and left to the TTL.
- `masking-service` purges maps older than `MASKING_MAP_TTL_HOURS` (default 336 h = 14 days, the hot
  tier retention, ADR-010) every `MASKING_PURGE_INTERVAL_SECONDS` (default 3600). `0` disables it.
  The purge is a `delete_by_query` with `conflicts=proceed`, safe on every replica at once.
- `mcp-server` gets tokens from `POST /tokens`, which computes them without storing anything.
  Tokens are `sha256(incident_id:kind:plaintext)`, so they match the ones the LLM saw.

**Consequences:** Incidents that are never reviewed keep their map until the TTL. A case that is
still pending after the TTL is shown with plaintext as before (case-service unmasked it when the
case was created), but tokens in new triage output for that incident can no longer be resolved.
`mcp-server` and `masking-service` must be upgraded together (`/tokens` is new).
