# ADR-023: Outbound integrations inform and record, they never act

**Status:** Accepted · **Date:** 2026-10-08

**Context:** Analysts need to hear about new cases (chat, e-mail), track approved cases in their ticketing system, and benefit from threat intelligence. These integrations send data to systems that are often SaaS, and some could be wired to take actions.

**Decision:**

- case-service publishes `esm.case-events` (`created`, `reviewed`); a separate `outbound-service` delivers them. case-service stays unaware of channels.
- Notifications go out for new cases above a severity threshold. By default they carry no hosts, users, IP addresses or LLM free text (`NOTIFY_DETAIL=summary`).
- Tickets are created only after an analyst approves a case (`TICKET_ON=approved` by default). An LLM suggestion alone never opens a ticket. Ticket sinks are idempotent per case (TheHive `sourceRef`, Jira label).
- Threat-intel lookups run in enrichment-service for external IPs only; the LLM receives a deterministic verdict next to the masked token.
- No adapter performs a response action (isolation, blocking, account changes). That remains a later, human-approved response-service (design rule 1, ROADMAP.md).
- Adapters use plain HTTP (`httpx`) and SMTP from the standard library; no vendor SDKs.

**Consequences:** a channel outage loses that notification (best effort, no duplicates elsewhere); ticket failures are retried through the bus and end in `esm.dlq`.
