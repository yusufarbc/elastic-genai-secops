[← Back to README](../../README.md)

# Logstash

Version **8.13.4**. One pipeline per log source, all defined in
[`integrations/sources`](../../integrations/sources/README.md) and enabled by its `pipelines.yml`.
The same files run on every target:

| Target | Pipelines | Settings |
| --- | --- | --- |
| Compose | `integrations/sources` mounted at `/etc/logstash/conf.d` | environment in `deploy/compose/siem.yml` |
| Bare metal | copied to `/etc/logstash/conf.d` by the installer | `/etc/default/logstash`; `ES_PW` in the Logstash keystore |
| Kubernetes | ConfigMap `esm-logstash-sources`, `pipelines.yml` in Secret `esm-logstash-pipelines` | ECK `Logstash` resource |

Ports and data streams are listed in [integrations/sources/README.md](../../integrations/sources/README.md#ports-and-data-streams).

## Adding a source

1. Create `integrations/sources/<source>/logstash.conf` with its own, unused port (above 1024).
2. Copy the `output { elasticsearch { ... } }` block from an existing pipeline; change only
   `data_stream_dataset`. Keep `data_stream_auto_routing => false` so fields in incoming events
   cannot redirect them.
3. Map fields to [ECS](https://www.elastic.co/guide/en/ecs/current/index.html) (`source.ip`,
   `destination.port`, `event.action`, `observer.*` ...) so detection rules and the triage
   pipeline understand them.
4. Add the pipeline to `integrations/sources/pipelines.yml`, the port to `deploy/compose/siem.yml`,
   the ConfigMap item to `deploy/kubernetes/base/kustomization.yaml` and `logstash.yaml`, and the
   port list to the installer summary.
5. Validate:

   ```bash
   docker run --rm -v "$PWD/integrations/sources:/etc/logstash/conf.d:ro" -e ES_PW=x \
     -e ES_CA_CERT=/etc/logstash/conf.d/pipelines.yml docker.elastic.co/logstash/logstash:8.13.4 \
     bin/logstash --config.test_and_exit -f /etc/logstash/conf.d/<source>/logstash.conf
   ```

   (`ES_CA_CERT` must point to any existing file for the syntax check.)

## Behaviour worth knowing

- Pipelines start before the bootstrap has created `logstash_ingest`; they log HTTP 401 for a
  minute and then recover on their own.
- FortiGate and PAN-OS timestamps carry no time zone. Set `FORTIGATE_TZ` / `PANOS_TZ` to the
  device clock's zone, otherwise events land hours off and rules miss them.
- Winlogbeat and the Filebeat `panw` module parse events in Elasticsearch ingest pipelines; the
  Windows and Palo Alto Beats pipelines pass `[@metadata][pipeline]` through. Load those ingest
  pipelines once per Beats version.
- Beats inputs have no TLS yet; restrict the ports to your client networks.
