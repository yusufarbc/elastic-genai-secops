# Roadmap

This repository consolidates three projects into one platform. Each phase ships as its own pull request.

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | History cleanup: removed committed installers (~118 MB) and scrubbed a hard-coded password, internal IPs and host names from all commits | Done |
| 1 | One layout, one license (Apache-2.0), one name (`esm` prefix); duplicates removed; ADRs split per decision | Done |
| 2 | Elastic content and first runnable profile: Logstash pipelines, ES roles/ILM/templates, detection rules in Kibana format, Sysmon config, compose `siem` profile, bare-metal installer rewrite | In review |
| 3 | Deployment: remaining compose layers (`fleet`, `ai-lite`, `full`), kustomize overlays (lab, on-prem, GKE), templated Windows endpoint rollout | Planned |
| 4 | Platform services: working builds, shared contracts (`libs/`), NATS bus, LLM providers (Ollama, OpenAI-compatible, Anthropic), case-service and bff APIs, compose `platform.yml`, end-to-end test | In review |
| 5 | MCP server rewrite: read-only masked tools, allow-listed hunts, stdio and bearer-token HTTP, optional Defender status (ADR-022) | In review |
| 6 | Outbound integrations: notifiers (Slack, Teams, email), ticketing (TheHive, Jira), threat intel (MISP, OpenCTI, AbuseIPDB) | Planned |
| 7 | CI/CD at the root: per-service lint and tests, config validation, secret scanning, image and IaC scanning, docs deploy | Planned |
| 8 | Documentation site (mkdocs-material) replacing `website/`, English translation of remaining Turkish content | Planned |

## Known issues carried into the next phases

### Phase 2 follow-ups

- The Kaspersky pipeline tags and stores events but does not parse the message yet (CEF/LEEF depending on the KSC export).
- WEB-* detection rules ship disabled: no web server log source is included yet.
- Beats → Logstash traffic is not encrypted (`ssl.enabled: false`); add an optional TLS input.
- Winlogbeat and Filebeat `panw` ingest pipelines must be loaded by hand once per version (`setup --pipelines`).

### Phase 3: Deployment

- `deploy/compose/docker-compose.yml` (platform dev stack) runs Elasticsearch with security disabled and duplicates the `siem` services; rebuild it as layers on top of `siem.yml`.
- No Fleet / Elastic Agent path yet (the invalid Fleet policy template was removed in phase 2).
- `deploy/kubernetes/base/eck/logstash.yaml` declares its Service with `apiVersion: networking.k8s.io/v1` (must be `v1`), targets the `default` namespace and an old cluster name; it should use the ECK `Logstash` resource and `integrations/sources`.
- `deploy/kubernetes/base/eck/fleet-server.yaml` binds `cluster-admin` and runs as root.
- `deploy/kubernetes/overlays/gke/gcs-snapshot-repo.yaml` contains a second YAML document without `apiVersion`/`kind`, so `kubectl apply` rejects it.
- case-service has no Kubernetes Service, so `CASE_SERVICE_URL` does not resolve.
- Kubernetes manifests mix Elastic 8.12 and 8.13; align them with `ELASTIC_VERSION` (8.13.4).
- Windows GPO scripts contain `ELK_SERVER_IP`, `DC_IP`, `PAN_FW_IP` and `\\FILESERVER` placeholders that must be set by hand; agent installers are no longer in git.

### Phase 4 follow-ups: platform services

- GCP Pub/Sub bus adapter (`BUS_BACKEND=pubsub`) is not implemented; only NATS JetStream.
- alert-gateway keeps open correlation windows in memory; alerts of an unfinished window are lost on restart.
- No asset-criticality, GeoIP or threat-intel enrichers in enrichment-service yet.
- Masking reverse maps have no TTL; access to masking-service is not restricted by network policy yet.
- `openai-compatible` is verified end to end with DeepSeek (`deepseek-flash`); `ollama` and `anthropic` only against mocked HTTP; `vertex` has no tests.
- No triage UI; analysts use the bff JSON API (and Kibana for the underlying alerts).
- Kubernetes manifests in `deploy/kubernetes/base/services` still use the old Pub/Sub settings; update them with the kustomize work in phase 3.

### Phase 5 follow-ups: MCP server

- Single shared bearer token; no per-analyst identity or audit of MCP tool calls yet.
- Only six hunts; add more to `content/hunting/hunts.yml` as sources are onboarded.
- `docs/deployment/kubernetes-master-guide.md` still describes the old MCP prototype.

### Phase 8: Documentation

- Still in Turkish: `docs/deployment/kubernetes-master-guide.md`, `docs/integrations/windows-audit-policy.md`, `deploy/endpoints/windows/gpo/GUIDE.tr.txt` and the GPO `.bat` / `.ps1` scripts.
- `docs/components/*.md` and `docs/operations/troubleshooting.md` still describe the old installer (enrollment token, port 5516 for Kaspersky, `logs-90d` policy).
