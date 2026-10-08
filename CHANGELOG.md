# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

First consolidated version of three earlier projects (an Ubuntu ELK installer, an MCP-based GenAI
SOC prototype and the Vigil AI-SOC platform).

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
  shellcheck, image builds with Trivy, GHCR publishing from `main`.
- End-to-end tests for the pipeline and the MCP server; architecture decision records ADR-001 to ADR-023.

### Changed

- Relicensed under Apache-2.0 (ADR-020); identifiers renamed to the `esm` prefix (ADR-021).

### Security

- Git history rewritten to remove a hard-coded password, internal IP addresses and host names, and
  committed installers.
