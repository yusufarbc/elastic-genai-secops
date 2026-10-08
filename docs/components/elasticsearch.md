[← Back to README](../../README.md)

# Elasticsearch

Version **8.13.4**, Basic license, security and TLS always on.

## Where it is configured

| Target | Configuration | TLS material |
| --- | --- | --- |
| Compose | environment in `deploy/compose/siem.yml` (single node, heap `ES_HEAP`) | `certs` volume, created by the `certs` service |
| Bare metal | `deploy/baremetal/ubuntu/config/elasticsearch.yml` (localhost only) | `/etc/elasticsearch/certs/{ca,http,transport}.{crt,key}` (PEM) |
| Kubernetes | `deploy/kubernetes/base/elasticsearch.yaml` (ECK); 3 nodes in `onprem`/`gke` | ECK secrets `esm-es-http-certs-*` |

`node.store.allow_mmap: false` is set on Kubernetes so no privileged `vm.max_map_count` init
container is needed (GKE Autopilot). Bare metal and Docker Desktop set `vm.max_map_count=262144`.

## Content loaded by `content/bootstrap.sh`

| Object | Name | Purpose |
| --- | --- | --- |
| ILM policy | `esm-logs` | Rollover at 50 GB per primary shard or 1 day (≤ 30 days retention) / 7 days; delete after `RETENTION_DAYS` |
| Component templates | `logs@custom`, `metrics@custom` | Attach `esm-logs` to the built-in `logs` and `metrics` index templates |
| Roles | `logstash_writer`, `esm_platform` | See [architecture overview](../architecture/overview.md#users-and-roles) |
| Users | `logstash_ingest`, `esm_platform` | Passwords from `.env`, `secrets.env` or `/root/esm-credentials` |

Using the `@custom` component templates keeps Elastic's own `logs`/`metrics` templates (ECS
mappings, data stream settings) and only overrides the lifecycle. A separate `logs-*-*` template
would never apply because the built-in one has a higher priority.

## Useful checks

```bash
ES=https://localhost:9200; AUTH="elastic:$ELASTIC_PASSWORD"; CA=--cacert ca.crt   # or -k in a lab
curl -s $CA -u "$AUTH" "$ES/_cluster/health?pretty"
curl -s $CA -u "$AUTH" "$ES/_data_stream/logs-*?filter_path=data_streams.name,data_streams.ilm_policy"
curl -s $CA -u "$AUTH" "$ES/logs-*/_ilm/explain?only_errors=true&pretty"
curl -s $CA -u "$AUTH" "$ES/_cat/indices/esm-*?v"
```

## Snapshots

The `gke` overlay registers the GCS repository `esm-gcs` and the daily SLM policy `esm-daily`
(`deploy/kubernetes/overlays/gke/gcs-snapshot-job.yaml`). For other targets register any
[snapshot repository](https://www.elastic.co/guide/en/elasticsearch/reference/8.13/snapshot-restore.html)
(shared file system, S3, MinIO) and an SLM policy the same way; the hot retention stays
`RETENTION_DAYS`.
