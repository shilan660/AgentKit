# Write Reference

Canonical reference for bulk ingest and other broad-impact write workflows.

## When to use

- the user wants to ingest many documents efficiently
- the user wants NDJSON bulk examples
- the user wants guidance on write safety or refresh behavior
- the user asks about by-query or reindex-like write workflows

## Task-specific notes

- Keep target indices explicit.
- Bulk, by-query, and reindex-like operations are low-freedom workflows: follow the documented sequence.
- Require explicit confirmation for broad or destructive mutations.

## Bulk ingest with NDJSON

**Method / Endpoint**:
```http
POST /_bulk
Content-Type: application/x-ndjson
```

**Body**:
```ndjson
{ "index": { "_index": "products", "_id": "sku-1001" } }
{ "sku": "sku-1001", "name": "Mechanical Keyboard", "price": 99.0 }
{ "index": { "_index": "products", "_id": "sku-1002" } }
{ "sku": "sku-1002", "name": "Trackpad", "price": 129.0 }
```

**Typical result shape**:
```json
{
  "errors": false,
  "items": [
    {
      "index": {
        "_index": "products",
        "_id": "sku-1001",
        "result": "created",
        "status": 201
      }
    }
  ]
}
```

## Bulk update example

**Method / Endpoint**:
```http
POST /_bulk
Content-Type: application/x-ndjson
```

**Body**:
```ndjson
{ "update": { "_index": "products", "_id": "sku-1001" } }
{ "doc": { "price": 89.0 } }
{ "update": { "_index": "products", "_id": "sku-1003" } }
{ "doc": { "price": 149.0 }, "doc_as_upsert": true }
```

## Refresh guidance

- default write behavior is usually enough for normal ingestion
- use `refresh=true` only when the user explicitly needs immediate search visibility
- avoid forcing refresh on large bulk loads unless the user accepts the throughput tradeoff

## High-impact write categories

Require explicit confirmation before suggesting or executing:

- `DELETE /<index>`
- `DELETE /<index>/_doc/<id>` when the user did not clearly identify the exact document
- `POST /<index>/_delete_by_query`
- `POST /<index>/_update_by_query`
- `POST /_reindex`

## By-query mutation guidance

1. restate the target index pattern and filter scope
2. preview the scope with a normal search first
3. warn that broad filters can touch many documents
4. require explicit confirmation before the mutation request

## Error handling guidance

- `errors: true` in bulk responses means at least one item failed even if the request returned `200 OK`
- inspect per-item `status` and `error` fields instead of assuming all writes succeeded
- partial failures are common in bulk flows; summarize successes and failures separately
