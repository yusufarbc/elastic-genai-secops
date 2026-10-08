# Security policy

## Reporting a vulnerability

Please do **not** open a public issue for security problems. Report them privately through
[GitHub security advisories](https://github.com/yusufarbc/Elastic-SecOps-Mastery/security/advisories/new).
Include the affected component, version or commit, steps to reproduce and the impact you expect.
You will get an acknowledgement within a week.

## Supported versions

Only the `production` branch receives fixes until the first tagged release.

## Security model in short

- The LLM receives only masked, curated incident data and can never trigger an action; analysts
  approve or reject every case (see the [design rules](ROADMAP.md#design-rules) and ADR-001 to ADR-004, ADR-022, ADR-023).
- `masking-service` is the only holder of plaintext reverse maps. Restrict network access to it.
- Kibana, the bff API and the Beats inputs are served without TLS by default; put them behind TLS
  and network restrictions before production use (listed in [ROADMAP.md](ROADMAP.md)).
- The MCP server requires a bearer token over HTTP and returns masked, read-only data.
- Container images run as non-root; CI scans them with Trivy and fails on fixable HIGH/CRITICAL
  findings.
