[← Back to README](../README.md)

# Logstash Component Guide

## Overview

Logstash is the data processing pipeline that ingests logs from various sources, parses and enriches them, and forwards them to Elasticsearch.

## Architecture

- **Binding**: `0.0.0.0` (LAN accessible)
- **Input Ports**:
  - 5044/tcp: Beats (FortiGate, etc.)
  - 5045/tcp: WEF/Winlogbeat
  - 5514/tcp+udp: Syslog RFC3164
  - 5515/tcp: Syslog RFC5424
  - 5516/tcp+udp: Kaspersky

## Configuration

### Pipeline Configuration

Location: `/etc/logstash/conf.d/`

The installation deploys multiple pipeline configurations:

1. **fortigate.conf**: FortiGate firewall logs via Beats
2. **windows_wef.conf**: Windows Event Forwarding logs
3. **syslog.conf**: Generic syslog (RFC3164)
4. **kaspersky.conf**: Kaspersky security logs

### Pipelines Definition

Location: `/etc/logstash/pipelines.yml`

Defines which configuration files to load and their settings.

## Input Configurations

### Beats Input (Port 5044)

For FortiGate and other Beats-based sources:

```ruby
input {
  beats {
    port => 5044
    ssl => false
  }
}
```

### Windows Event Forwarding (Port 5045)

Receives logs from Winlogbeat on Windows Event Collector:

```ruby
input {
  beats {
    port => 5045
    ssl => false
  }
}
```

### Syslog RFC3164 (Port 5514)

Traditional syslog format:

```ruby
input {
  syslog {
    port => 5514
    type => "syslog"
  }
}
```

### Syslog RFC5424 (Port 5515)

Modern syslog format with structured data:

```ruby
input {
  tcp {
    port => 5515
    codec => syslog {
      syslog_version => "rfc5424"
    }
  }
}
```

### Kaspersky (Port 5516)

Kaspersky Security Center logs:

```ruby
input {
  tcp {
    port => 5516
    codec => json
  }
  udp {
    port => 5516
    codec => json
  }
}
```

## Filter Patterns

### ECS Normalization

All pipelines normalize data to Elastic Common Schema (ECS):

```ruby
filter {
  mutate {
    add_field => {
      "[@metadata][target_index]" => "logs-windows-default"
      "event.dataset" => "windows.forwarded"
      "event.module" => "windows"
    }
  }
}
```

### Grok Parsing

Example for syslog:

```ruby
filter {
  grok {
    match => { "message" => "%{SYSLOGBASE} %{GREEDYDATA:message}" }
    overwrite => [ "message" ]
  }
}
```

### Date Parsing

```ruby
filter {
  date {
    match => [ "timestamp", "ISO8601", "yyyy-MM-dd HH:mm:ss" ]
    target => "@timestamp"
  }
}
```

## Output Configuration

### Elasticsearch Output

All pipelines output to Elasticsearch:

```ruby
output {
  elasticsearch {
    hosts => ["https://localhost:9200"]
    user => "logstash_ingest"
    password => "${ES_PW}"
    cacert => "/etc/logstash/certs/ca.crt"
    index => "%{[@metadata][target_index]}"
    action => "create"
  }
}
```

### Credentials

- **User**: `logstash_ingest`
- **Password**: Stored in Logstash keystore as `ES_PW`
- **CA Certificate**: `/etc/logstash/certs/ca.crt`

## Keystore Management

### Environment Variable

Keystore password is stored in `/etc/default/logstash`:

```bash
LOGSTASH_KEYSTORE_PASS="<random_password>"
```

### Adding Secrets

```bash
echo "password" | sudo /usr/share/logstash/bin/logstash-keystore \
  --path.settings /etc/logstash add --force ES_PW
```

### Listing Keys

```bash
sudo /usr/share/logstash/bin/logstash-keystore \
  --path.settings /etc/logstash list
```

## Data Streams

Logstash writes to data streams following the pattern:

```
logs-<dataset>-default
```

Examples:
- `logs-windows-default`
- `logs-fortigate-default`
- `logs-syslog-default`
- `logs-kaspersky-default`

## Pipeline Testing

### Validate Configuration

```bash
sudo /usr/share/logstash/bin/logstash \
  --path.settings /etc/logstash -t
```

### Test with Sample Data

```bash
echo "test message" | nc localhost 5514
```

## Monitoring

### Service Status

```bash
sudo systemctl status logstash
```

### Logs

```bash
tail -f /var/log/logstash/logstash-plain.log
journalctl -u logstash -f
```

### Pipeline Stats

```bash
curl -s http://localhost:9600/_node/stats/pipelines?pretty
```

## Performance Tuning

### Pipeline Workers

Edit `/etc/logstash/logstash.yml`:

```yaml
pipeline.workers: 4
pipeline.batch.size: 125
pipeline.batch.delay: 50
```

### JVM Heap

Edit `/etc/logstash/jvm.options`:

```
-Xms2g
-Xmx2g
```

## Common Operations

### Restart Service

```bash
sudo systemctl restart logstash
```

### Reload Configuration

Logstash automatically reloads configuration changes if enabled:

```yaml
config.reload.automatic: true
config.reload.interval: 3s
```

### View Active Pipelines

```bash
curl -s http://localhost:9600/_node/pipelines?pretty
```

## Troubleshooting

See [Troubleshooting Guide](troubleshooting.md#logstash) for common issues and solutions.
