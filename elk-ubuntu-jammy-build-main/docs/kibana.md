[← Back to README](../README.md)

# Kibana Component Guide

## Overview

Kibana is the visualization and management interface for the ELK Stack. It provides dashboards, search capabilities, and administrative tools.

## Architecture

- **Binding**: `0.0.0.0:5601` (LAN accessible)
- **Protocol**: HTTP (consider reverse proxy with TLS for production)
- **Backend**: Connects to Elasticsearch via `https://localhost:9200`

## Configuration

### Main Configuration File

Location: `/etc/kibana/kibana.yml`

Key settings:
```yaml
server.port: 5601
server.host: "0.0.0.0"
elasticsearch.hosts: ["https://localhost:9200"]
elasticsearch.ssl.certificateAuthorities: ["/etc/kibana/certs/ca.crt"]
```

### Encryption Keys

Kibana requires encryption keys for security features. These are stored in `/etc/kibana/kibana.env`:

```bash
KBN_SECURITY_KEY=<random_key>
KBN_SAVEDOBJ_KEY=<random_key>
KBN_REPORTING_KEY=<random_key>
```

The installation script generates these automatically using:
```bash
/usr/share/kibana/bin/kibana-encryption-keys generate
```

### Systemd Integration

Keys are loaded via systemd drop-in at `/etc/systemd/system/kibana.service.d/10-env.conf`:

```ini
[Service]
EnvironmentFile=-/etc/kibana/kibana.env
```

## Initial Setup

### Enrollment Process

1. **Generate Enrollment Token** (on Elasticsearch server):
```bash
sudo /usr/share/elasticsearch/bin/elasticsearch-create-enrollment-token -s kibana
```

2. **Configure Kibana** (automatic during installation):
```bash
sudo /usr/share/kibana/bin/kibana-setup --enrollment-token <token>
```

3. **Access Kibana**:
   - URL: `http://<server_ip>:5601`
   - Username: `elastic`
   - Password: (from installation output)

### First Login

After enrollment, Kibana will:
- Configure Elasticsearch connection
- Set up TLS verification
- Enable security features
- Create initial user session

## Features

### Discover

Search and explore your data:
- Full-text search across all indices
- Field filtering and aggregations
- Time-based queries
- Save searches for reuse

### Dashboards

Create visualizations:
- Charts, graphs, and metrics
- Geo maps
- Time series analysis
- Custom layouts

### Stack Management

Administrative tasks:
- Index pattern management
- Index lifecycle policies
- User and role management
- Saved objects

## Index Patterns

### Creating Index Patterns

1. Navigate to **Stack Management** → **Index Patterns**
2. Click **Create index pattern**
3. Enter pattern: `logs-*-*`
4. Select time field: `@timestamp`
5. Click **Create**

### Common Patterns

- `logs-windows-*`: Windows event logs
- `logs-fortigate-*`: FortiGate logs
- `logs-syslog-*`: Syslog messages
- `logs-kaspersky-*`: Kaspersky logs

## Security

### User Management

Create additional users:

1. **Stack Management** → **Security** → **Users**
2. Click **Create user**
3. Assign roles:
   - `kibana_admin`: Full Kibana access
   - `viewer`: Read-only access
   - `editor`: Read and write access

### Role-Based Access Control

Define custom roles:

1. **Stack Management** → **Security** → **Roles**
2. Click **Create role**
3. Configure:
   - Cluster privileges
   - Index privileges
   - Kibana privileges

## Monitoring

### Service Status

```bash
sudo systemctl status kibana
```

### Logs

```bash
tail -f /var/log/kibana/kibana.log
journalctl -u kibana -f
```

### Health Check

```bash
curl -s http://localhost:5601/api/status | jq .
```

## Common Operations

### Restart Service

```bash
sudo systemctl restart kibana
```

### Regenerate Encryption Keys

```bash
sudo /usr/share/kibana/bin/kibana-encryption-keys generate -q --force
```

Update `/etc/kibana/kibana.env` with new keys and restart.

### Reset Configuration

If enrollment fails, reset and try again:

```bash
sudo rm -f /etc/kibana/kibana.yml
sudo systemctl restart kibana
# Re-run enrollment process
```

## Performance Tuning

### Node.js Memory

Edit `/etc/systemd/system/kibana.service.d/override.conf`:

```ini
[Service]
Environment="NODE_OPTIONS=--max-old-space-size=2048"
```

### Response Timeout

In `kibana.yml`:

```yaml
elasticsearch.requestTimeout: 30000
elasticsearch.shardTimeout: 30000
```

## Dashboards and Visualizations

### Importing Dashboards

1. **Stack Management** → **Saved Objects**
2. Click **Import**
3. Select NDJSON file
4. Resolve conflicts if needed

### Creating Visualizations

1. **Visualize Library** → **Create visualization**
2. Select visualization type:
   - Bar chart
   - Line chart
   - Pie chart
   - Data table
   - Metric
   - Tag cloud
3. Configure data source and aggregations
4. Save visualization

## Alerting

### Creating Alerts

1. **Stack Management** → **Rules and Connectors**
2. Click **Create rule**
3. Configure:
   - Rule type (e.g., Index threshold)
   - Conditions
   - Actions (email, webhook, etc.)

### Connectors

Set up notification channels:
- Email
- Slack
- Webhook
- PagerDuty

## Troubleshooting

See [Troubleshooting Guide](troubleshooting.md#kibana) for common issues and solutions.

## Best Practices

1. **Regular Backups**: Export saved objects regularly
2. **Index Pattern Management**: Keep patterns organized
3. **User Access**: Follow principle of least privilege
4. **Dashboard Organization**: Use spaces to organize dashboards
5. **Performance**: Monitor query performance and optimize
