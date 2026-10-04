[← Back to README](../README.md)

# Kibana Internals and Visualization Architecture

## 1. The Plugin System and Saved Objects
Kibana 5.0 introduced a formalized plugin architecture. A critical component is the **Saved Objects** service, managing persistence of dashboards, visualizations, and index patterns.

### 1.1 The .kibana Index
Saved Objects are serialized and stored as JSON documents in a dedicated Elasticsearch index (`.kibana` or `.kibana_<version>`).

### 1.2 Multi-Tenancy via Spaces
To support **Spaces** (isolated environments), Kibana modified the Saved Object schema.
*   **Namespace Field**: Documents include a namespace (e.g., `namespace: "marketing"`). Default space has no namespace.
*   **Isolation Strategy**: The Kibana server-side client automatically injects a filter for the current space's namespace into every Elasticsearch query.

### 1.3 Shareable Objects
Recent architectures support **Shareable Saved Objects** using a `namespaceType` field. This allows objects to be designated as "multiple," enabling a single visualization to exist in multiple spaces simultaneously by storing an array of namespace identifiers, avoiding data duplication.
