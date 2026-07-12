# Diagnostics Reference

Use this reference for non-destructive cluster diagnostics.

## When to use

- the user asks for cluster health
- searches are timing out and you need high-level status
- you need a safe first look before deeper troubleshooting
- you want to identify engine/version before planning data-plane requests

## Safety and compatibility guidance

- Keep this reference non-destructive.
- Privilege required: cluster visibility endpoints may need monitor or admin permissions depending on the deployment.
- Engine/version discovery, health, and cat APIs are useful preflight checks before deeper troubleshooting.

## Root endpoint for preflight

**Method / Endpoint**:
```http
GET /
```

**Typical result shape**:
```json
{
  "name": "search-node-1",
  "cluster_name": "production-search",
  "version": {
    "number": "2.11.0"
  },
  "tagline": "The OpenSearch Project: https://opensearch.org/"
}
```

## Cluster health

```http
GET /_cluster/health
```

**Typical result shape**:
```json
{
  "cluster_name": "production-search",
  "status": "green",
  "number_of_nodes": 6,
  "active_primary_shards": 128
}
```

## Cat nodes

```http
GET /_cat/nodes?v&format=json
```

## Cat shards

```http
GET /_cat/shards?v&format=json
```

## Interpretation guidance

- `green` means primaries and replicas are allocated.
- `yellow` usually means unassigned replicas.
- `red` means one or more primary shards are unavailable.
- the root endpoint often reveals engine flavor and version, which can explain compatibility or auth differences.

## Safety guidance

- Use health and cat APIs before suggesting invasive remediation.
- Avoid cluster setting changes unless the user explicitly asks for them.
