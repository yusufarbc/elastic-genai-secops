# Kibana Component Guide

## 1. Overview and Architecture
Kibana provides the visualization layer for the Stack.

### Service Details
- **Binding**: `0.0.0.0:5601`.
- **Backend**: Connects to ES via `https://localhost:9200`.
- **Peristence**: Saved objects are stored in the `.kibana` index in Elasticsearch.

---

## 2. Configuration & Internals

### 2.1 Main Configuration (`kibana.yml`)
```yaml
server.port: 5601
server.host: "0.0.0.0"
elasticsearch.hosts: ["https://localhost:9200"]
elasticsearch.ssl.certificateAuthorities: ["/etc/kibana/certs/ca.crt"]
```

### 2.2 Encryption Keys
Required for Alerting and Reporting.
```bash
/usr/share/kibana/bin/kibana-encryption-keys generate
```

### 2.3 The Saved Objects Architecture
Kibana 5.0+ uses a formalized plugin architecture.
- **`.kibana` Index**: All dashboards, visualizations, and patterns are serialized JSON documents in this index.
- **Spaces (Multi-Tenancy)**:
    - Kibana injects a "namespace" filter into every query to isolate data between Spaces (e.g., Marketing vs. Security).
    - **Shareable Objects**: Uses `namespaceType` to allow a single dashboard to exist in multiple spaces without duplication.

---

## 3. Features & Usage

### 3.1 Discover & Dashboards
- **Discover**: Full-text search and time-based filtering.
- **Dashboards**: Aggregations of visualizations.

### 3.2 Index Patterns
To visualize data, map Elasticsearch indices to Kibana patterns:
1.  **Stack Management** → **Index Patterns**.
2.  Create `logs-*-*` with `@timestamp`.

### 3.3 Security & Users
- **Roles**: Create roles with specific index privileges (e.g., `read` only on `logs-windows-*`).
- **Spaces**: Restrict user access to specific Spaces for isolation.

---

## 4. Key Operations

**Regenerate Keys**:
```bash
sudo /usr/share/kibana/bin/kibana-encryption-keys generate -q --force
```

**Health Check**:
```bash
curl -s http://localhost:5601/api/status | jq .
```
