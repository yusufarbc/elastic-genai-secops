# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

First consolidated version of three earlier projects (an Ubuntu ELK installer, an MCP-based GenAI
SOC prototype and an AI-SOC platform).

### Fixed

- Repository links, clone instructions and README badge point to the renamed repository
  (`elastic-genai-secops`), its `production` branch and the current pipeline workflow.

### Changed

- **CI/CD**: one DevSecOps pipeline for the `staging` → `production` flow (ADR-024): golangci-lint
  with gosec, Semgrep, CodeQL, govulncheck, pip-audit, Trivy IaC and image scans, Syft SBOMs, e2e on
  the compose stack, OWASP ZAP API scan, cosign-signed images with provenance and SBOM attestations.
- Relicensed under Apache-2.0 (ADR-020); identifiers renamed to the `esm` prefix (ADR-021).

### Added

- **SIEM profile** on three targets: Docker Compose (`deploy/compose/siem.yml`), bare-metal Ubuntu
  22.04 installer, Kubernetes with ECK 3.5 and kustomize (`lab`, `onprem`, `gke` overlays).
- **Log sources** (`integrations/sources`): Windows (Winlogbeat, WEF, Sysmon), FortiGate, Palo Alto
  (syslog and Filebeat panw), Kaspersky, syslog RFC3164/5424, Metricbeat/Heartbeat; GeoIP for firewalls.
- **Detection content**: 30 MITRE-mapped Kibana rules, ILM policy `esm-logs`, roles and users
  loaded by `content/bootstrap.sh`; allow-listed hunting queries.
- **AI triage pipeline** over NATS JetStream: detection-service, alert-gateway (correlation),
  enrichment-service, masking-service, llm-orchestrator, case-service, bff.
- **LLM providers**: mock, Ollama, OpenAI-compatible (verified with DeepSeek), Anthropic, Vertex AI;
  token budget per window and an audit record per call.
- **MCP server**: read-only, masked tools; stdio or bearer-token HTTP.
- **Outbound integrations**: Slack, Teams, webhook and e-mail notifications; TheHive and Jira
  tickets after analyst approval; AbuseIPDB and MISP threat intel for external IPs.
- **Windows endpoint rollout** via GPO startup scripts and `prepare-share.ps1` (verified downloads).
- **CI**: Go and Python lint/tests, rule and manifest validation (kubeconform with ECK schemas),
  shellcheck, image builds with Trivy, GHCR publishing from `production`.
- End-to-end tests for the pipeline and the MCP server; architecture decision records ADR-001 to ADR-023.

### Security

- Git history rewritten to remove a hard-coded password, internal IP addresses and host names, and
  committed installers.
