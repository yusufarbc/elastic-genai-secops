# Roadmap

This repository consolidates three projects into one platform. Each phase ships as its own pull request.

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | History cleanup: removed committed installers (~118 MB) and scrubbed a hard-coded password, internal IPs and host names from all commits | Done |
| 1 | One layout, one license (Apache-2.0), one name (`esm` prefix); duplicates removed; ADRs split per decision | Done |
| 2 | Elastic content: fix Logstash pipelines, ES roles, ILM, convert detection rules to Kibana format, Sysmon config | Next |
| 3 | Deployment: layered Compose profiles, kustomize overlays (lab, on-prem, GKE), bare-metal installer fixes, templated Windows endpoint rollout | Planned |
| 4 | Platform services: working builds, shared contracts, `Bus` (NATS / Pub/Sub), LLM providers (Ollama, OpenAI-compatible, Anthropic), case-service and bff APIs | Planned |
| 5 | MCP server rewrite: correct FastMCP API, stdio and authenticated HTTP, allow-listed read-only tools, optional Defender endpoint mode | Planned |
| 6 | Outbound integrations: notifiers (Slack, Teams, email), ticketing (TheHive, Jira), threat intel (MISP, OpenCTI, AbuseIPDB) | Planned |
| 7 | CI/CD at the root: per-service lint and tests, config validation, secret scanning, image and IaC scanning, docs deploy | Planned |
| 8 | Documentation site (mkdocs-material) replacing `website/`, English translation of remaining Turkish content | Planned |

## Known issues carried into the next phases

### Phase 2: Elastic content

- Logstash pipelines bind conflicting ports (`fortigate` and `paloalto-beats` on 5044, `winlogbeat` and `wef` on 5045) and `paloalto-syslog` binds privileged port 514.
- `integrations/sources/pipelines.yml` still points at bare-metal paths and lists only 3 of the 9 pipelines.
- `integrations/sources/windows/translate/windows_event_codes.yml` is missing; the installer creates an empty one.
- `logstash_writer` role covers only `logs-*-*` (Metricbeat writes to `metrics-*`), and `setup_logstash_ingest.sh` replaces the role of the `logstash_ingest` user.
- Deprecated `ssl` / `cacert` options in Elasticsearch outputs.
- `content/detection-rules/legacy/siem.rules.yml` is a custom YAML format (not importable), targets `winlogbeat-*` instead of `logs-windows*`, and contains leftover citation markers and Turkish playbooks.
- `sysmon.xml` excludes process and network events under `C:\Windows\`, hiding LOLBin activity.
- `content/fleet/windows-endpoint-policy.json` is not a valid Fleet API payload.

### Phase 3: Deployment

- `deploy/compose/docker-compose.yml` runs Elasticsearch with security disabled, and its Logstash service is not functional.
- `deploy/kubernetes/base/eck/logstash.yaml` declares its Service with `apiVersion: networking.k8s.io/v1` (must be `v1`), targets the `default` namespace and an old cluster name.
- `deploy/kubernetes/base/eck/fleet-server.yaml` binds `cluster-admin` and runs as root.
- `deploy/kubernetes/overlays/gke/gcs-snapshot-repo.yaml` contains a second YAML document without `apiVersion`/`kind`, so `kubectl apply` rejects it.
- case-service has no Kubernetes Service, so `CASE_SERVICE_URL` does not resolve.
- Elastic versions are mixed (8.11, 8.12, 8.13); the bare-metal installer is unpinned.
- Windows GPO scripts contain `ELK_SERVER_IP`, `DC_IP`, `PAN_FW_IP` and `\\FILESERVER` placeholders that must be set by hand; agent installers are no longer in git.

### Phase 4: Platform services

- Go `go.sum` files are empty; Python `pyproject.toml` files use a non-existent build backend.
- Bus adapters are no-ops, so nothing flows end-to-end yet. `CI` is manual-only until builds pass.
- Async tests in `llm-orchestrator` and `enrichment-service` call `asyncio.get_event_loop()`, which fails on Python 3.14 (they pass on 3.12); switch to `pytest-asyncio` or `asyncio.run`.
- `alert-gateway` ignores `CORRELATION_THRESHOLD`; `BudgetTracker` never resets; the LLM audit log goes to stdout only.

### Phase 5: MCP server

- `services/mcp-server/server.py` imports a non-existent module (`mcp.server.fastapi`), has no authentication, and runs PowerShell with `shell=True`.

### Phase 8: Documentation

- Still in Turkish: `docs/deployment/kubernetes-master-guide.md`, `docs/integrations/windows-audit-policy.md`, `deploy/endpoints/windows/gpo/GUIDE.tr.txt`, installer messages and some config comments.
