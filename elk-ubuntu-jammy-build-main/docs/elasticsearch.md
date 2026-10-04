[← Back to README](../README.md)

# Elasticsearch Component Guide

## Overview

Elasticsearch is the core search and analytics engine of the ELK Stack. In this deployment, it runs on `localhost:9200` with TLS encryption enabled for security.

## Architecture

- **Binding**: `localhost` only (not accessible from network)
- **Protocol**: HTTPS with TLS
- **Port**: 9200
- **Certificate**: Self-signed CA with HTTP and Transport certificates

## Configuration

### Main Configuration File

Location: `/etc/elasticsearch/elasticsearch.yml`

Key settings:
```yaml
cluster.name: elk-lab
node.name: elk-node-1
network.host: localhost
http.port: 9200

# Security
xpack.security.enabled: true
xpack.security.http.ssl.enabled: true
xpack.security.transport.ssl.enabled: true
```

### TLS Certificates

The installation script generates three types of certificates:

1. **CA Certificate** (`ca.crt`, `ca.key`)
   - Root certificate authority
   - Used to sign HTTP and Transport certificates

2. **HTTP Certificate** (`http.crt`, `http.key`, `http.p12`)
   - For HTTPS API access
   - PKCS#12 format for enrollment token generation
   - SAN: localhost, 127.0.0.1, ::1

3. **Transport Certificate** (`transport.crt`, `transport.key`)
   - For node-to-node communication
   - Required even for single-node setups

All certificates are stored in `/etc/elasticsearch/certs/`.

## Security

### Built-in Users

- **elastic**: Superuser account (password set during installation)
- **logstash_ingest**: Custom user for Logstash writes

### Roles

- **logstash_writer**: Custom role with permissions:
  - Cluster: `monitor`
  - Indices `logs-*-*`: `create_index`, `write`, `create`, `view_index_metadata`

## Index Lifecycle Management (ILM)

### Policy: logs-90d

Automatically deletes indices after 90 days:

```json
{
  "policy": {
    "phases": {
      "hot": { "actions": {} },
      "delete": { 
        "min_age": "90d", 
        "actions": { "delete": {} } 
      }
    }
  }
}
```

### Index Template: logs-default

Applies to all log indices:
- Pattern: `logs-*-*`, `fortigate-logs-*`
- Shards: 1
- Replicas: 0 (single node)
- ILM policy: `logs-90d`

## API Access

### Health Check

```bash
curl -s --cacert /etc/elasticsearch/certs/ca.crt https://localhost:9200
```

### Cluster Health

```bash
curl -s --cacert /etc/elasticsearch/certs/ca.crt \
  -u elastic:<password> \
  https://localhost:9200/_cluster/health?pretty
```

### List Indices

```bash
curl -s --cacert /etc/elasticsearch/certs/ca.crt \
  -u elastic:<password> \
  https://localhost:9200/_cat/indices?v
```

### Data Streams

```bash
curl -s --cacert /etc/elasticsearch/certs/ca.crt \
  -u elastic:<password> \
  https://localhost:9200/_data_stream?pretty
```

## Performance Tuning

### Memory Settings

Elasticsearch uses `/etc/systemd/system/elasticsearch.service.d/override.conf` for environment variables:

```ini
[Service]
Environment="ES_PATH_CONF=/etc/elasticsearch"
Environment="ES_LOG_DIR=/var/log/elasticsearch"
```

Heap size is configured in `/etc/elasticsearch/jvm.options`:
```
-Xms4g
-Xmx4g
```

### Kernel Parameters

The installation script sets:
```bash
vm.max_map_count=262144
```

## Logs

- **Location**: `/var/log/elasticsearch/`
- **Main log**: `elasticsearch.log`
- **Slow query log**: `elasticsearch_index_search_slowlog.log`

View logs:
```bash
tail -f /var/log/elasticsearch/elasticsearch.log
journalctl -u elasticsearch -f
```

## Common Operations

### Restart Service

```bash
sudo systemctl restart elasticsearch
```

### Check Status

```bash
sudo systemctl status elasticsearch
```

### Reset elastic Password

```bash
sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic -i
```

### Create Enrollment Token

```bash
sudo /usr/share/elasticsearch/bin/elasticsearch-create-enrollment-token -s kibana
```

## Troubleshooting

See [Troubleshooting Guide](troubleshooting.md#elasticsearch) for common issues and solutions.
