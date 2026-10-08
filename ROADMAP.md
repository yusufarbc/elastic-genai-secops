# Roadmap

This repository consolidates three projects into one platform. Each phase ships as its own pull request.

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | History cleanup: removed committed installers (~118 MB) and scrubbed a hard-coded password, internal IPs and host names from all commits | Done |
| 1 | One layout, one license (Apache-2.0), one name (`esm` prefix); duplicates removed; ADRs split per decision | Done |
| 2 | Elastic content and first runnable profile: Logstash pipelines, ES roles/ILM/templates, detection rules in Kibana format, Sysmon config, compose `siem` profile, bare-metal installer rewrite | In review |
| 3a | Kubernetes: ECK 3.5 + kustomize (`base`, `components/platform`, `components/production`, overlays `lab`/`onprem`/`gke`), bootstrap Job, GCS snapshots | In review |
| 3b | Fleet / Elastic Agent (compose layer and ECK `Agent`), templated Windows endpoint rollout | Planned |
| 4 | Platform services: working builds, shared contracts (`libs/`), NATS bus, LLM providers (Ollama, OpenAI-compatible, Anthropic), case-service and bff APIs, compose `platform.yml`, end-to-end test | In review |
| 5 | MCP server rewrite: read-only masked tools, allow-listed hunts, stdio and bearer-token HTTP, optional Defender status (ADR-022) | In review |
| 6 | Outbound integrations: case events, outbound-service (Slack, Teams, webhook, e-mail; TheHive, Jira), threat intel in enrichment (AbuseIPDB, MISP) (ADR-023) | In review |
| 7 | CI/CD at the root: per-service lint and tests, config validation, secret scanning, image and IaC scanning, docs deploy | Planned |
| 8 | Documentation site (mkdocs-material) replacing `website/`, English translation of remaining Turkish content | Planned |

## Known issues carried into the next phases

### Phase 2 follow-ups

- The Kaspersky pipeline tags and stores events but does not parse the message yet (CEF/LEEF depending on the KSC export).
- WEB-* detection rules ship disabled: no web server log source is included yet.
- Beats → Logstash traffic is not encrypted (`ssl.enabled: false`); add an optional TLS input.
- Winlogbeat and Filebeat `panw` ingest pipelines must be loaded by hand once per version (`setup --pipelines`).

### Phase 3 follow-ups: deployment

- No Fleet / Elastic Agent path yet (phase 3b).
- Windows GPO scripts contain `ELK_SERVER_IP`, `DC_IP`, `PAN_FW_IP` and `\\FILESERVER` placeholders that must be set by hand; agent installers are no longer in git.
- Kubernetes: only `lab` was deployed and tested (kind, Kubernetes 1.37, ECK 3.5); `onprem` and `gke` are schema-validated but not deployed. No NetworkPolicies, no Ingress for Kibana, no HPA.
- Logstash's monitoring API runs without TLS inside the cluster (ECK 3.5 + Logstash 8.13 TLS API returns empty replies).
- ILM deletes on the hot tier do not wait for a snapshot (`wait_for_snapshot`); the gke overlay snapshots daily and keeps 14 days hot.
- The bare-metal installer has not been run on a real Ubuntu 22.04 host yet.

### Phase 6 follow-ups: outbound integrations

- Verified end to end with a local webhook catcher (Slack format, generic webhook, TheHive API shape); not yet against real Slack, Teams, SMTP, TheHive or Jira instances, nor live AbuseIPDB / MISP.
- No OpenCTI adapter yet; no GeoIP or asset-criticality enrichers.
- Failed notifications are not retried (by design); there is no delivery report in the case.

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
