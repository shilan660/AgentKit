# Index Reference

Use this reference for index CRUD, mappings, settings, aliases, and compatibility-safe cutovers.

## When to use

- the user wants to list or inspect indices
- the user needs to create an index with mappings or settings
- the user needs field types before writing a query
- the user needs shard or replica settings
- the user wants to delete an index or switch an alias safely

## Safety and compatibility guidance

- These examples use shared Elasticsearch/OpenSearch REST APIs.
- Privilege required: index inspection usually needs index read or monitor permissions; create/update/delete usually needs index admin permissions.
- Prefer aliases for cutovers or logical renames; direct rename flows are not universal.
- Require explicit confirmation before deleting an index.

## List indices

**Method / Endpoint**:
```http
GET /_cat/indices?v&format=json
```

**Typical result shape**:
```json
[
  {
    "health": "green",
    "status": "open",
    "index": "products-v1",
    "docs.count": "124556",
    "store.size": "1.2gb"
  }
]
```

## Check whether an index exists

**Method / Endpoint**:
```http
HEAD /products
```

**Expected result**:
- `200 OK` if the index exists
- `404 Not Found` if the index does not exist

## Create an index

**Method / Endpoint**:
```http
PUT /products
Content-Type: application/json
```

**Body**:
```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
      "sku": { "type": "keyword" },
      "name": { "type": "text" },
      "price": { "type": "float" },
      "created_at": { "type": "date" }
    }
  }
}
```

**Typical result shape**:
```json
{
  "acknowledged": true,
  "shards_acknowledged": true,
  "index": "products"
}
```

## Get index details

### Get mapping

**Method / Endpoint**:
```http
GET /products/_mapping
```

**Typical result shape**:
```json
{
  "products": {
    "mappings": {
      "properties": {
        "sku": { "type": "keyword" },
        "name": { "type": "text" },
        "price": { "type": "float" },
        "created_at": { "type": "date" }
      }
    }
  }
}
```

### Get settings

**Method / Endpoint**:
```http
GET /products/_settings
```

### Get aliases

**Method / Endpoint**:
```http
GET /_alias
```

## Update index settings

Use this for safe/common dynamic settings such as replica count. Do not imply that every setting is dynamically updateable.

**Method / Endpoint**:
```http
PUT /products/_settings
Content-Type: application/json
```

**Body**:
```json
{
  "index": {
    "number_of_replicas": 2
  }
}
```

**Typical result shape**:
```json
{
  "acknowledged": true
}
```

## Safe alias cutover

Use aliases when the user wants a logical name to point to a new backing index.

**Method / Endpoint**:
```http
POST /_aliases
Content-Type: application/json
```

**Body**:
```json
{
  "actions": [
    { "remove": { "index": "products-v1", "alias": "products" } },
    { "add": { "index": "products-v2", "alias": "products" } }
  ]
}
```

**Typical result shape**:
```json
{
  "acknowledged": true
}
```

## Delete an index

Destructive operation. Require explicit confirmation before suggesting or executing it.

**Method / Endpoint**:
```http
DELETE /products
```

**Typical result shape**:
```json
{
  "acknowledged": true
}
```

## Interpretation guidance

- `text` fields are analyzed and suited to full-text search.
- `keyword` fields are suited to exact filtering and aggregations.
- Mappings explain why `term` vs `match` behaves differently.
- Settings help identify shard counts, replicas, and custom analyzers.
