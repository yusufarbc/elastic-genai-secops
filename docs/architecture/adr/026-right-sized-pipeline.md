# ADR-026: A pipeline sized for a small open-source project

**Status:** Accepted · **Date:** 2026-10-10 · Amends the pipeline stages in ADR-024

**Context:** ADR-024 put every scanner on every pull request: CodeQL and Semgrep, Trivy image
scans, Syft SBOMs, a 20-minute end-to-end run with an OWASP ZAP API scan, and cosign signatures with
SLSA provenance and SBOM attestations on release, plus an OpenSSF Scorecard workflow. The project
has one maintainer, nobody deploys the published images yet, and most of the stack is upstream
Elastic images. A pull request into `staging` took 25–30 minutes, and several checks repeated each
other or answered questions nobody asks yet.

The project still ships its own code (nine services, about 5,000 lines of Go and Python) that
handles attacker-influenced log data, personal data (masking-service) and HTTP requests (bff,
mcp-server), so code-level checks stay.

**Decision:**

- **Keep on every change:** lint (golangci-lint with gosec, ruff, hadolint, shellcheck,
  actionlint), gitleaks over the full history, unit tests, rule and manifest validation, CodeQL,
  govulncheck, pip-audit, dependency review, Trivy IaC.
- **Remove:** Semgrep (overlaps CodeQL and gosec), the OWASP ZAP API scan (one internal JSON API
  with security headers set in code), Syft SBOMs, cosign signatures and attestations, and the
  Scorecard workflow.
- **Run less often:** Trivy image scans only on the weekly run and by hand (findings come from
  base images, which Dependabot updates); the end-to-end test only on promotion PRs into
  `production` and by hand.
- `Pipeline gate` stays the single required check, so the rulesets do not change.

**Alternatives considered:**

- Keep ADR-024 as is: release confidence the project does not need yet, paid with a 25-minute wait
  on every change.
- Only lint, tests, gitleaks and dependency scans: also drops CodeQL, which is free for public
  repositories and the only SAST left.

**Consequences:** A PR into `staging` takes about 5–10 minutes. A change that breaks the running
stack is caught at promotion instead of at the `staging` PR; run the e2e job by hand for risky
changes. Published images cannot be verified with cosign; anyone deploying them should pin digests.

**Revisit when:** other people deploy the GHCR images (add signing and SBOM attestations back), the
bff or a triage UI is exposed beyond the internal network (add DAST back), or more maintainers join.
