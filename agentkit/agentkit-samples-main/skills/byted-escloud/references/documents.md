# Documents Reference

Canonical reference for single-document create, get, update, upsert, and delete workflows.

## When to use

- the user wants to insert one document
- the user wants to fetch a document by ID
- the user wants to update part of a document
- the user wants upsert behavior when a document may not exist yet
- the user wants to delete one document safely

## Task-specific notes

- Use `_doc` paths for cross-engine compatibility.
- Routine writes are fine when the target index and document scope are explicit.
- Deletes are low-freedom operations: confirm the exact target before proceeding.
- Use `refresh=true` only when immediate visibility is required.

## Index a document with an explicit ID

**Method / Endpoint**:
```http
PUT /products/_doc/sku-1001
Content-Type: application/json
```

**Body**:
```json
{
  "sku": "sku-1001",
  "name": "Mechanical Keyboard",
  "price": 99.0,
  "created_at": "2026-04-15T10:30:15Z"
}
```

**Typical result shape**:
```json
{
  "_index": "products",
  "_id": "sku-1001",
  "result": "created"
}
```

## Create a document with an auto-generated ID

**Method / Endpoint**:
```http
POST /products/_doc
Content-Type: application/json
```

**Body**:
```json
{
  "sku": "sku-1002",
  "name": "Trackpad",
  "price": 129.0,
  "created_at": "2026-04-15T10:35:00Z"
}
```

**Typical result shape**:
```json
{
  "_index": "products",
  "_id": "Q9f...generated-id",
  "result": "created"
}
```

## Get a document by ID

**Method / Endpoint**:
```http
GET /products/_doc/sku-1001
```

**Typical result shape**:
```json
{
  "_index": "products",
  "_id": "sku-1001",
  "found": true,
  "_source": {
    "sku": "sku-1001",
    "name": "Mechanical Keyboard",
    "price": 99.0
  }
}
```

## Update part of a document

**Method / Endpoint**:
```http
POST /products/_update/sku-1001
Content-Type: application/json
```

**Body**:
```json
{
  "doc": {
    "price": 89.0,
    "updated_at": "2026-04-15T11:00:00Z"
  }
}
```

**Typical result shape**:
```json
{
  "_index": "products",
  "_id": "sku-1001",
  "result": "updated"
}
```

## Upsert when the document may not exist

**Method / Endpoint**:
```http
POST /products/_update/sku-1003
Content-Type: application/json
```

**Body**:
```json
{
  "doc": {
    "name": "USB-C Dock",
    "price": 149.0,
    "updated_at": "2026-04-15T11:05:00Z"
  },
  "doc_as_upsert": true
}
```

**Typical result shape**:
```json
{
  "_index": "products",
  "_id": "sku-1003",
  "result": "created"
}
```

## Write with immediate refresh

**Method / Endpoint**:
```http
PUT /products/_doc/sku-1004?refresh=true
Content-Type: application/json
```

## Delete a document

Destructive operation.

**Method / Endpoint**:
```http
DELETE /products/_doc/sku-1001
```

**Typical result shape**:
```json
{
  "_index": "products",
  "_id": "sku-1001",
  "result": "deleted"
}
```
