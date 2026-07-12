# Data Plane - Quickstart, Inspection, and Reference-Driven Workflows

Use `scripts/data.py` for endpoint validation, smoke-testing a new cluster, and safe inspection. Use `references/*.md` plus ad-hoc `curl` or Python snippets for richer Elasticsearch/OpenSearch workflows.

## Command prefix

```bash
{baseDir}/venv/bin/python {baseDir}/scripts/data.py --endpoint <endpoint> <command>
```

## Decision rule

- Use `data.py` for routine connectivity validation, new-cluster smoke tests, and common inspection.
- Use `references/*.md` plus ad-hoc snippets for task-specific search, aggregation, alias, bulk, and migration work.

## Reference routing

- Not sure where to start, or the task spans multiple steps -> [references/patterns.md](references/patterns.md)
- Connectivity, auth, TLS, privilege, or endpoint reachability -> [references/connectivity.md](references/connectivity.md)
- Cluster health, nodes, shards, or safe diagnostics -> [references/diagnostics.md](references/diagnostics.md)
- Indices, mappings, settings, or aliases -> [references/index.md](references/index.md)
- Single-document create/get/update/delete patterns -> [references/documents.md](references/documents.md)
- Search, filters, highlighting, or pagination -> [references/search.md](references/search.md)
- Aggregations, grouped counts, trends, or percentiles -> [references/aggregation.md](references/aggregation.md)
- Bulk ingest, broad writes, or by-query/reindex-like operations -> [references/write.md](references/write.md)

## Connection and auth

Auth options:
- Basic auth: `--username <user> --password <pass>`
- API key: `--api-key <value>`
- Bearer token: `--bearer-token <value>`

Use exactly one auth mode per invocation.

TLS options:
- `--ca-certs <path>` for a custom CA bundle
- `--insecure` to disable certificate verification

Environment variable defaults:
- `ESCLOUD_ENDPOINT`
- `ESCLOUD_USERNAME`
- `ESCLOUD_PASSWORD`
- `ESCLOUD_CA_CERTS`
- `ESCLOUD_INSECURE`
- `ESCLOUD_API_KEY`
- `ESCLOUD_BEARER_TOKEN`

## Connectivity preflight

Before any data-plane read or write, run:

```bash
data.py --endpoint <https://domain:9200> info
```

If `info` fails, stop and verify endpoint reachability, allowlist/public exposure, credentials, and TLS settings.

## Commands

### info

```bash
data.py --endpoint <endpoint> info
```

### smoke_test

Creates a disposable test index, indexes one sample document, reads it back, and runs a simple search.

```bash
data.py --endpoint <endpoint> smoke_test
```

Optional flags:
- `--index <name>` (default: `escloud-smoke-test`)
- `--doc-id <id>`
- `--reuse-existing`
- `--cleanup --confirm`

If the test index already exists, `smoke_test` refuses to proceed unless `--reuse-existing` is passed.

### index_exists

```bash
data.py --endpoint <endpoint> index_exists --index <name>
```

### index_list

```bash
data.py --endpoint <endpoint> index_list
```

### index_get

Returns settings, mappings, and aliases for an index.

```bash
data.py --endpoint <endpoint> index_get --index <name>
```

### cluster_health

```bash
data.py --endpoint <endpoint> cluster_health
```

### cat_nodes

```bash
data.py --endpoint <endpoint> cat_nodes
```

### cat_shards

```bash
data.py --endpoint <endpoint> cat_shards
```

## Agent guidance

- Do not add fixed `data.py` subcommands for one-off data-plane tasks by default.
- Prefer the smallest useful `curl` command or Python snippet for the user's actual schema, filters, and auth mode.
- Require explicit confirmation before destructive or high-impact requests.
