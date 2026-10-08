# ADR-024: `staging` → `production` branch flow and a single DevSecOps pipeline

**Status:** Accepted · **Date:** 2026-10-08 · Supersedes the branch names in ADR-011

**Context:** ADR-011 named the branches `test` and `main` and split CI and security scanning across
two workflows. The repository now uses `staging` (integration) and `production` (default, release),
and there is no automatic deployment target yet, so the pipeline must give release confidence on its
own: tests, static and dynamic security testing, and a traceable artifact.

**Decision:**

- Branches: feature branches → PR into `staging` → PR from `staging` into `production` (merge
  commit). `hotfix/*` may go straight to `production`. Enforced by repository rulesets and a
  promotion guard job.
- One workflow (`.github/workflows/pipeline.yml`) runs on every PR and push to both branches:
  lint → secret scan → unit tests → content validation → SAST (CodeQL, Semgrep, gosec) →
  SCA (govulncheck, pip-audit, dependency review) → IaC (Trivy) → image build → image scan (Trivy)
  → SBOM (Syft) → end-to-end test on the compose stack with the mock LLM → DAST (OWASP ZAP API scan)
  → gate → release (GHCR push, cosign signature, provenance and SBOM attestations).
- A single `Pipeline gate` job is the only required status check, so rulesets do not need to track
  individual job names.
- Full end-to-end and DAST run on every PR, not only before production: the repository is public, so
  runner minutes are free, and finding a regression at the `staging` PR is cheaper than at promotion.

**Alternatives considered:**

- Keep separate CI and security workflows: two places to look, and no single gate.
- E2E/DAST only on PRs into `production`: faster feedback on `staging`, but `staging` could hold
  changes that break the stack.
- GitFlow with release branches: more ceremony than a two-branch project needs.

**Rationale:** One gate for one question ("can this be promoted?"); every scanner reports to the
Security tab; published images are reproducible from a commit, signed, and carry their SBOM.

**Follow-ups:** add a deploy job per GitHub Environment once a target exists (ADR-009); extend the
ZAP scan to Kibana-facing endpoints if the triage UI (phase 7) adds them.
