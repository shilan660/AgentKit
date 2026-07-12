# Search Reference

Canonical reference for search, filtering, highlighting, and deterministic pagination.

## When to use

- the user wants matching documents
- the user needs recent logs, traces, or events
- the user needs field-level filters or sorted results
- the user wants matched snippets or a focused sample set

## Task-specific notes

- Adapt field names, filters, and `_source` to the user's schema.
- Use `match`, `match_phrase`, or `multi_match` for analyzed text fields.
- Use `term` or `terms` for exact values, usually on `.keyword` fields.
- Keep pagination deterministic with explicit sorts.
- If the user already knows the ID, route to `documents.md` instead of search.

## Basic text search

**Method / Endpoint**:
```http
POST /logs-*/_search
Content-Type: application/json
```

**Body**:
```json
{
  "size": 10,
  "query": {
    "match": {
      "message": "error"
    }
  },
  "_source": ["@timestamp", "level", "service", "message"]
}
```

## Filtered query

```json
{
  "size": 20,
  "sort": [
    { "@timestamp": "desc" },
    { "_id": "asc" }
  ],
  "query": {
    "bool": {
      "filter": [
        { "term": { "level.keyword": "ERROR" } },
        { "term": { "service.keyword": "api" } },
        { "range": { "@timestamp": { "gte": "now-24h" } } }
      ]
    }
  },
  "_source": ["@timestamp", "service", "message", "trace_id"]
}
```

## Highlighting

```json
{
  "size": 10,
  "query": {
    "match_phrase": {
      "message": "connection timeout"
    }
  },
  "highlight": {
    "fields": {
      "message": {}
    }
  }
}
```

## Multi-field search

```json
{
  "size": 10,
  "query": {
    "multi_match": {
      "query": "timeout error",
      "fields": ["message", "error_details", "stack_trace"],
      "type": "best_fields"
    }
  }
}
```

## Deterministic pagination with `search_after`

**First page body**:
```json
{
  "size": 20,
  "sort": [
    { "@timestamp": "desc" },
    { "_id": "asc" }
  ],
  "query": {
    "range": {
      "@timestamp": { "gte": "now-24h" }
    }
  }
}
```

**Next page body**:
```json
{
  "size": 20,
  "sort": [
    { "@timestamp": "desc" },
    { "_id": "asc" }
  ],
  "search_after": ["2026-04-15T10:30:15Z", "A1b2C3"],
  "query": {
    "range": {
      "@timestamp": { "gte": "now-24h" }
    }
  }
}
```

## Expected result shape

```json
{
  "hits": {
    "total": { "value": 145 },
    "hits": [
      {
        "_index": "logs-2026.04.15",
        "_id": "A1b2C3",
        "sort": ["2026-04-15T10:30:15Z", "A1b2C3"],
        "_source": {
          "@timestamp": "2026-04-15T10:30:15Z",
          "level": "ERROR",
          "service": "api",
          "message": "Connection timeout"
        }
      }
    ]
  }
}
```
