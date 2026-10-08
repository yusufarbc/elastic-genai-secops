# CI/CD and DevSecOps pipeline

One workflow, [`.github/workflows/pipeline.yml`](../../.github/workflows/pipeline.yml), builds, tests
and security-scans every change. The decision record is [ADR-024](../architecture/adr/024-staging-production-pipeline.md).

## Branch flow

```
feature/*  --PR-->  staging  --PR (merge commit)-->  production
hotfix/*   --PR---------------------------------->  production   (then merge production back into staging)
```

- `production` is the default branch and the release line. `staging` is where changes are
  integrated and verified first.
- Work happens on short-lived branches and reaches `staging` through a pull request.
- `production` accepts pull requests only from `staging` (or `hotfix/*`). The `Guard · promotion
  path` job rejects anything else.
- Dependabot opens its pull requests against `staging`.

Both branches are protected by repository rulesets ([`.github/rulesets/`](../../.github/rulesets)):
no direct pushes, no force pushes, no deletion, and the **`Pipeline gate`** check must pass. Apply
or update them with:

```bash
gh api -X POST repos/{owner}/{repo}/rulesets --input .github/rulesets/staging.json
gh api -X POST repos/{owner}/{repo}/rulesets --input .github/rulesets/production.json
# update an existing one: gh api -X PUT repos/{owner}/{repo}/rulesets/<id> --input <file>
```

## Stages

| Stage | Job | Tools | Fails the pipeline on |
| --- | --- | --- | --- |
| 0 guard | `promotion` | — | PR into `production` not from `staging`/`hotfix/*` |
| 1 quality | `lint` | gofmt, go vet, golangci-lint + **gosec**, ruff, hadolint, shellcheck, actionlint | any finding |
| | `secrets` | **gitleaks** (full git history) | any leak not in `.gitleaksignore` |
| 2 verify | `test-go`, `test-python` | go test -race, pytest (coverage) | failing test |
| | `content` | rule build check, `docker compose config`, kustomize + kubeconform (ECK CRDs) | invalid content or manifest |
| | `sast-codeql` | **CodeQL** (Go, Python, GitHub Actions; security-extended) | alerts are reported in the Security tab |
| | `sast-semgrep` | **Semgrep** (default, Go, Python, Dockerfile, Actions rule packs) | ERROR-severity finding |
| | `sca` | **govulncheck** (reachable Go vulns), **pip-audit** (all Python packages) | any known vulnerability |
| | `dependency-review` | GitHub dependency review (PRs) | new HIGH/CRITICAL dependency |
| | `iac` | **Trivy** config (Dockerfiles, Kubernetes, compose) | HIGH/CRITICAL misconfiguration |
| 3 build | `build` (per service) | buildx, **Trivy** image scan, **Syft SBOM** (CycloneDX) | HIGH/CRITICAL CVE with a fix |
| | `sbom-source` | **Syft** repository SBOM | — |
| 4 dynamic | `e2e-dast` | compose stack, `tests/e2e/pipeline_test.py`, `mcp_client_test.py`, **OWASP ZAP** API scan of the bff ([`openapi.yaml`](../../services/bff/openapi.yaml)) | e2e failure or a High ZAP alert |
| 5 gate | `gate` | — | any job above failed or was cancelled |
| 6 release | `release` (push only) | GHCR push, **cosign** keyless signing, SLSA build provenance and SBOM attestations | — |

SAST, IaC and image findings are uploaded as SARIF and appear under **Security → Code scanning**.
SBOMs, coverage, ZAP reports and the compose logs of the e2e run are attached to each workflow run
as artifacts. The LLM is always `LLM_PROVIDER=mock`; CI never calls a billed API.

The weekly scheduled run re-scans `production` (secrets, SAST, SCA, IaC, image CVEs) without the
e2e stage, so newly published CVEs surface even when nothing changes. A separate
[`scorecard.yml`](../../.github/workflows/scorecard.yml) workflow runs the OpenSSF Scorecard.

## Published images

A push to `staging` or `production` (that is, a merged pull request) publishes every service to
`ghcr.io/<owner>/elastic-secops-mastery/<service>`, the name the Kubernetes manifests use:

| Branch | Tags |
| --- | --- |
| `production` | `latest`, `<sha12>` |
| `staging` | `staging`, `<sha12>` |

Each image is signed and carries provenance and SBOM attestations. Verify with:

```bash
cosign verify ghcr.io/<owner>/elastic-secops-mastery/bff:latest \
  --certificate-identity-regexp 'https://github.com/<owner>/.+/.github/workflows/pipeline.yml@.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
gh attestation verify oci://ghcr.io/<owner>/elastic-secops-mastery/bff:latest --owner <owner>
```

## Deployment

There is no automatic deployment target yet. The release job already runs in the GitHub
Environment named after the branch (`staging`, `production`), so a deploy job can be added later
with environment secrets and required reviewers, for example `kubectl apply` of an overlay with
the image digest from the release job.

## Tuning a gate

- **False-positive secret:** add the fingerprint printed by gitleaks to `.gitleaksignore` with a comment.
- **Semgrep:** add `# nosemgrep: <rule-id>` with a reason on the line.
- **Trivy (IaC or image):** fix it; if it cannot be fixed, add the ID to a `.trivyignore` with a reason and an expiry.
- **golangci-lint / gosec:** `//nolint:<linter> // reason` on the line, or adjust `.golangci.yml`.
- **ZAP:** a `.zap/rules.tsv` (`<rule id>\tIGNORE\t<reason>`) can be passed with `-c`; only High alerts fail the build.
