# ADR-009: Stateful operations baseline: 3-node MVP cluster, ILM, GCS snapshots

**Status:** Accepted · **Date:** 2026-06-30

**Context:** Elasticsearch pods run 24/7 in containers, but "staying up" is an *active* state achieved by correct configuration, not a passive one. A disk-full or OOM cluster is "up but not working."

**Decisions:**
- **Cluster size (MVP):** 3 nodes — gives master quorum and avoids split-brain; no need for a large cluster at MVP.
- **StatefulSet + PersistentVolumeClaim:** managed by ECK so each pod re-binds to its own disk on restart.
- **PodDisruptionBudget + anti-affinity:** prevent all nodes landing on one physical machine / all dying together.
- **Resource requests/limits:** size RAM so heap (≈half of pod RAM) is sufficient; otherwise pods OOM-restart.
- **ILM from day one:** hot tier holds **14 days** of searchable data; after 14 days, snapshot then delete from hot tier to free disk. SOC log volume fills disk fast — without ILM the cluster jams within days (disk >85% flips indices read-only).

**Rationale:** These are the infrastructure that *makes* "always up" true. ECK automates the heavy lifting (StatefulSet orchestration, rolling upgrades, cluster formation); our job is ILM, snapshots, resource planning, and monitoring.

**Risks / follow-ups:** Test snapshot *restore*, not just snapshot. Monitor disk utilization actively.
