# Volcano Engine ESCloud / CloudSearch Skill

`byted-escloud` helps an agent operate Volcano Engine (Volcengine) **ESCloud / CloudSearch** clusters and work with their Elasticsearch/OpenSearch data plane.

## What this skill can do

### Control plane

Use this skill to manage cluster lifecycle tasks such as:
- create a cluster
- inspect cluster details and status
- scale or reconfigure a cluster
- enable public access and manage related networking settings
- restart, rename, or delete a cluster safely

### Data plane

Use this skill to help with Elasticsearch/OpenSearch work such as:
- validate connectivity, auth, and TLS
- smoke-test a new cluster
- inspect cluster health, nodes, shards, and index metadata
- create or inspect mappings, settings, aliases, documents, queries, aggregations, and bulk patterns
- generate task-specific `curl` commands or short Python snippets for one-off workflows

## How to use this skill

### In OpenClaw

Install this repo under your OpenClaw skills directory, for example:

- `.openclaw/skills/byted-escloud/`

Then enable it in `.openclaw/openclaw.json`:

```json
{
  "skills": {
    "entries": {
      "byted-escloud": {
        "enabled": true,
        "env": {
          "VOLCENGINE_ACCESS_KEY": "...",
          "VOLCENGINE_SECRET_KEY": "...",
          "VOLCENGINE_REGION": "cn-beijing"
        }
      }
    }
  }
}
```

### Required and optional configuration

Control-plane operations use:
- `VOLCENGINE_ACCESS_KEY`
- `VOLCENGINE_SECRET_KEY`
- optional: `VOLCENGINE_REGION` (defaults to `cn-beijing`)

Data-plane helper commands can use:
- `ESCLOUD_ENDPOINT`
- `ESCLOUD_USERNAME`, `ESCLOUD_PASSWORD`
- `ESCLOUD_API_KEY`
- `ESCLOUD_BEARER_TOKEN`
- `ESCLOUD_CA_CERTS`
- `ESCLOUD_INSECURE`

### Local helper CLI usage

This repo includes helper CLIs under `scripts/`. Create a virtualenv and install dependencies:

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Common examples:

```bash
# Control plane
./venv/bin/python ./scripts/control.py list
./venv/bin/python ./scripts/control.py detail --id <instance-id>

# Data-plane validation and inspection
./venv/bin/python ./scripts/data.py --endpoint <https://domain:9200> info
./venv/bin/python ./scripts/data.py --endpoint <https://domain:9200> cluster_health
./venv/bin/python ./scripts/data.py --endpoint <https://domain:9200> index_list

# Smoke test a new cluster
./venv/bin/python ./scripts/data.py --endpoint <https://domain:9200> smoke_test
./venv/bin/python ./scripts/data.py --endpoint <https://domain:9200> smoke_test --cleanup --confirm
```

## How the data-plane part works

- Use `scripts/data.py` for routine validation, smoke tests, and safe inspection.
- Use the docs in [`references/`](references/) for richer Elasticsearch/OpenSearch workflows.
- For variant needs, let the agent generate ad-hoc `curl` or Python snippets instead of forcing everything into a fixed CLI.

A good entry point for richer workflows is [references/patterns.md](references/patterns.md).

## Example prompts

- "List my Volcengine ESCloud instances."
- "Show details for ESCloud instance `<id>`."
- "Create an ESCloud cluster named `search-prod` in VPC `<vpc>` subnet `<subnet>` with 3 masters and 2 hot nodes."
- "Open public access for this cluster and add my IP to the allowlist."
- "Quickly test whether `<endpoint>` is usable, then show cluster health and index metadata."
- "Build a query for timeout logs from the last 24 hours."
- "Write a short Python script to bulk ingest these NDJSON documents."

## Important safety rules

- Before any data-plane read or write, run `data.py --endpoint <endpoint> info` first.
- Use `data.py smoke_test` when validating a new cluster; if the test index already exists, pass `--reuse-existing` or choose a different `--index`.
- Cleanup for the smoke test is destructive and requires `--cleanup --confirm`.
- Destructive or high-impact operations should always be explicitly confirmed.

## More documentation

- [SKILL.md](SKILL.md) - skill routing and guardrails
- [CONTROL_PLANE.md](CONTROL_PLANE.md) - lifecycle workflows
- [CONTROL_TOOLS.md](CONTROL_TOOLS.md) - fine-grained control-plane tools
- [DATA_PLANE.md](DATA_PLANE.md) - helper CLI and data-plane operating model
- [references/patterns.md](references/patterns.md) - detailed ES/OpenSearch workflow references
