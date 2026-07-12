# Aggregation Reference

Use this reference when the user wants grouped counts, trends, percentiles, or rollups instead of raw documents.

## When to use

- counts by service, host, tenant, or status
- hourly or daily trends
- percentiles for latency or size metrics
- nested breakdowns such as service -> error type
- summary answers that are cheaper than exporting raw documents

## Core guidance

- Prefer `size: 0` when only aggregations matter.
- Use `.keyword` fields for terms aggregations when available.
- Add time filters for logs and metrics.
- Keep bucket sizes bounded.
- Prefer summaries over raw exports for large datasets.
- These examples use aggregation APIs shared by Elasticsearch and OpenSearch.

## Terms aggregation

**Method / Endpoint**:
```http
POST /logs-*/_search
Content-Type: application/json
```

**Body**:
```json
{
  "size": 0,
  "aggs": {
    "services": {
      "terms": {
        "field": "service.keyword",
        "size": 10
      }
    }
  }
}
```

## Time-series aggregation

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "term": { "level.keyword": "ERROR" } },
        { "range": { "@timestamp": { "gte": "now-24h" } } }
      ]
    }
  },
  "aggs": {
    "errors_over_time": {
      "date_histogram": {
        "field": "@timestamp",
        "fixed_interval": "1h"
      }
    }
  }
}
```

## Nested breakdown

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "term": { "level.keyword": "ERROR" } },
        { "range": { "@timestamp": { "gte": "now-24h" } } }
      ]
    }
  },
  "aggs": {
    "by_service": {
      "terms": {
        "field": "service.keyword"
      },
      "aggs": {
        "by_error_type": {
          "terms": {
            "field": "error_type.keyword"
          }
        }
      }
    }
  }
}
```

## Percentiles

```json
{
  "size": 0,
  "aggs": {
    "endpoints": {
      "terms": {
        "field": "endpoint.keyword",
        "size": 20
      },
      "aggs": {
        "latency_percentiles": {
          "percentiles": {
            "field": "response_time_ms",
            "percents": [50, 95, 99]
          }
        }
      }
    }
  }
}
```

## Expected result shape

```json
{
  "aggregations": {
    "by_service": {
      "buckets": [
        { "key": "api", "doc_count": 120 },
        { "key": "worker", "doc_count": 73 }
      ]
    }
  }
}
```
