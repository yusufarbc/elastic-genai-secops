# Elasticsearch Component Guide

## 1. Overview and Architecture
Elasticsearch is the core search and analytics engine of the ELK Stack, running on `localhost:9200` with TLS encryption enabled.

### Service Details
- **Binding**: `localhost` only.
- **Protocol**: HTTPS with TLS.
- **Port**: 9200.
- **Certificate**: Self-signed CA with separate HTTP and Transport certificates.

---

## 2. Configuration & Internals

### 2.1 Main Configuration (`elasticsearch.yml`)
```yaml
cluster.name: elk-lab
node.name: elk-node-1
network.host: localhost
http.port: 9200
xpack.security.enabled: true
xpack.security.http.ssl.enabled: true
xpack.security.transport.ssl.enabled: true
```

### 2.2 Inverted Index and Immutability
Elasticsearch relies on Lucene's **inverted index** (mapping terms to documents) and **immutable segments**.
*   **No Locking**: Segments are never modified, allowing lock-free reads.
*   **Page Cache**: OS can aggressively cache these immutable files, maximizing RAM usage.

### 2.3 Compression (Frame of Reference)
*   **Delta Encoding**: Stores differences between IDs (e.g., 5, 3) instead of raw IDs (100, 105, 108).
*   **PForDelta**: Handles outliers efficiently to keep block sizes small.

### 2.4 BKD Trees
Used for numeric and geo-spatial data.
*   **Performance**: Optimized for range queries and nearest-neighbor searches.
*   **Selective Indexing**: Acts like an R-Tree for high-dimensional spatial filtering.

---

## 3. Distributed Mechanics

### 3.1 Zen2 Consensus
A deterministic cluster coordination algorithm introduced in v7.0.
*   **Voting Configs**: Decouples active nodes from voting nodes.
*   **Term & Epochs**: Uses "Term" counters to handle split-brain scenarios deterministically.

### 3.2 Translog & Durability
1.  Document is indexed into memory buffer + appended to **Translog**.
2.  **Refresh**: Buffer to new segment (searchable).
3.  **Fsync**: Translog is fsync'ed to disk before ACK.

---

## 4. Index Lifecycle Management (ILM)

### Policy: logs-90d
Automatically deletes indices after 90 days.
```json
{
  "policy": {
    "phases": {
      "delete": { 
        "min_age": "90d", 
        "actions": { "delete": {} } 
      }
    }
  }
}
```

---

## 5. Security & Access

### Users & Roles
- **elastic**: Superuser (Bootstrap password).
- **logstash_writer**: Custom role restricted to `logs-*-*` indices.

### API Cheatsheet
**Health Check**:
```bash
curl -s --cacert /etc/elasticsearch/certs/ca.crt https://localhost:9200
```

**Cluster Health**:
```bash
curl -s --cacert /etc/elasticsearch/certs/ca.crt -u elastic:<password> https://localhost:9200/_cluster/health?pretty
```

For troubleshooting, check `/var/log/elasticsearch/elasticsearch.log`.
