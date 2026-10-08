# ADR-022: MCP server is read-only and returns masked data

**Status:** Accepted · **Date:** 2026-10-08

**Context:** The Elastic-GenAI-SOC prototype exposed an MCP server that ran arbitrary Elasticsearch queries, started Defender scans through `shell=True` PowerShell, and had no authentication. An MCP client is itself an LLM, often a hosted one, so everything the server returns leaves the platform and is attacker-influenced input for that model (CLAUDE.md sections 5 and 6).

**Decision:**

- Tools are read-only: list/get cases, alert statistics, allow-listed hunts. No tool changes case state, endpoints or configuration; analyst decisions stay in the case API.
- Case data is pseudonymized with the incident's masking tokens before it is returned, the same tokens the triage LLM saw. Analyst notes and reviewer names are not exposed.
- Hunts are fixed queries in `content/hunting/hunts.yml`; they return hit counts and top values of fields that do not identify hosts, users, accounts or IPs (enforced when the file is loaded).
- HTTP transport requires a bearer token (`MCP_TOKEN`, constant-time comparison) and keeps the SDK's DNS-rebinding protection on; stdio is for local use.
- The Defender tool survives only as an optional, Windows-only, read-only status call with a fixed argument list.

**Alternatives considered:** returning unmasked data to trusted clients (rejected: the client model and its provider are outside the platform's control); allowing free KQL queries (rejected: unbounded data exposure and prompt-injection surface).

**Consequences:** analysts see tokens in their assistant and resolve them in the case API or Kibana. The `esm_platform` role gains read access to `logs-*-*` and `metrics-*-*` for hunts.
