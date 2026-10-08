# ADR-008: Elasticsearch self-hosted via ECK on GKE (open source, AGPLv3/ELv2) — NOT Elastic Cloud

**Status:** Accepted · **Date:** 2026-06-30

**Context:** Goal is a fully free, open-source, self-hosted stack aligned with the "digital sovereignty" philosophy. Two separate concepts were clarified: (a) software *license* — Elasticsearch/Kibana are open source again since Sept 2024 (AGPLv3 added alongside SSPL and ELv2); self-hosted use inside our own application is free and permitted under ELv2/AGPLv3. (b) deployment *model* — Elastic Cloud is a paid *managed operations service*, not a license cost.

**Alternatives considered:**
- Elastic Cloud (managed) — rejected: it's a paid subscription for operations and conflicts with the self-hosted/sovereignty goal, even though the underlying software is free.
- GCP-native search alternative (e.g. OpenSearch fork) — rejected: the architecture is built around Elastic's detection/SIEM/vector features; switching is a large change.
- ECK on GKE, self-hosted — **chosen.**

**Rationale:** Self-hosting under AGPLv3/ELv2 is free and sovereignty-aligned. ELv2 only forbids reselling Elasticsearch as a managed service — which we don't do. The org-specific RAG store (ADR-003) can live inside the same self-hosted Elasticsearch via `dense_vector`/ELSER — no separate vector DB needed (verify ELSER's license tier; fall back to `dense_vector` + self-hosted embeddings if ELSER is not in Basic).

**Trade-off accepted:** The stateful SRE burden (storage management, snapshots, rolling upgrades, shard rebalancing, JVM/heap tuning, cluster health) is **ours**, by deliberate choice. This is not a mistake to avoid — it is the cost of sovereignty. With a two-person team, manage it by starting small and automating early (ADR-009).

**Risks / follow-ups:** Verify which Elastic features (detection rules, ML jobs, entity risk scoring, ELSER, searchable snapshots) are available in the free/Basic tier before depending on them; record any paid dependency here.
