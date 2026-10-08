# ADR-011: Engineering process: GitHub two-branch flow, DevSecOps CI/CD, GKE deploy

**Status:** Accepted · **Date:** 2026-06-30 · Branch names superseded by [ADR-024](024-staging-production-pipeline.md)

**Context:** SOLID design, CI/CD pipeline, DevSecOps cycle required.

**Decisions:**
- **Branches:** `test` (integration) and `main` (release); PRs into `main` require a green pipeline.
- **CI/CD (GitHub Actions) gates:** lint → unit tests → SAST → dependency/SCA scan → container build → image vulnerability scan → IaC scan → push image to registry → deploy. Fail on high-severity findings.
- **Testing:** unit tests per service; contract tests at boundaries; one end-to-end integration test driving a synthetic incident with a **mocked LLM** — never hit the billed API in CI.
- **Cost guardrail:** the queue (Pub/Sub) is the cost gate; `llm-orchestrator` has a per-window budget circuit-breaker — when exceeded, queue incidents for human triage instead of calling the API.

**Rationale:** Aligns with the stated SOLID + DevSecOps goals and protects against runaway API spend and untested releases.

**Risks / follow-ups:** Keep secrets out of code (use Workload Identity, ADR-006). Monitor LLM cost, request rate, and triage latency as first-class metrics.
