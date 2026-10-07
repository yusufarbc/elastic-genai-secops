# ADR-016: GKE Autopilot (NOT standard node pool)

**Status:** Accepted · **Date:** 2026-06-30 · **Amended by:** [ADR-019](019-deployment-profiles-and-targets.md)

**Context:** Two GKE cluster modes: Standard (user manages node pools, machine types, OS) and Autopilot (Google manages nodes; workloads define resource requests, GKE provisions accordingly).

**Alternatives considered:**
- GKE Standard — more control; allows privileged init containers (needed for ES `vm.max_map_count` sysctl).
- GKE Autopilot — **chosen:** eliminates node management overhead; security posture is stronger (Autopilot blocks privileged containers and hostPath mounts by default); no node-pool sizing decisions for a two-person team.

**Rationale:** Autopilot is the right default for a two-person team: no node sizing, no OS patch management, no manual cluster upgrades. The only friction is Elasticsearch's `vm.max_map_count` requirement — resolved by setting `node.store.allow_mmap: false` in the ECK manifest, which instructs ES to use `niofs` instead of `mmapfs`. Performance impact is acceptable for SOC log volumes at MVP scale.

**Risks / follow-ups:**
- `node.store.allow_mmap: false` → niofs is slower than mmapfs for large segment merges. Re-evaluate if indexing throughput becomes a bottleneck; at that point, migrate to a Standard node pool with a privileged DaemonSet to set the sysctl.
- All custom service containers (`runAsNonRoot: true`, `seccompProfile: RuntimeDefault`) must comply with Autopilot's restricted pod security standard.
