# Control Tools - Low-Level ESCloud API Operations

Fallback control-plane reference for operations not covered by goal-based `control.py`; shared guardrails from [SKILL.md](SKILL.md) apply here.

## Command prefix

```bash
{baseDir}/venv/bin/python {baseDir}/scripts/control_tools.py <command>
```

## Output contract

Commands return JSON success payloads under `status/data`, or error payloads under `error/details`.

## Fallback-only rules

- Prefer `control.py` for normal lifecycle workflows.
- Use this file for granular, API-shaped, or uncovered operations.
- For destructive operations, resolve and show the exact target first, require explicit user confirmation, then pass the required confirmation flag.

## Common intents

| Intent | Command(s) |
|---|---|
| List instances (fallback) | `list` |
| Inspect one instance | `detail --id <id>` |
| Discover VPCs/subnets/zones/specs | `vpc`, `subnet --vpc-id <id>`, `zones`, `node_specs`, `versions` |
| Create an instance | `create ...` |
| Scale one node type | `scale ...` |
| Manage allowlists | `ip_allowlist_get`, `ip_allowlist_set` |
| Manage public network/EIP | `public_network`, `eip_list`, `eip_allocate`, `eip_release` |
| Reset password | `reset_password` |
| Rename / maintenance / restart | `rename`, `maintenance_set`, `restart_node` |
| Delete instance | `delete --id <id> --confirm` |

## Discovery commands

### list

```bash
control_tools.py list [--page-number <n>] [--page-size <n>]
```

### detail

```bash
control_tools.py detail --id <instance-id>
```

### vpc

```bash
control_tools.py vpc
```

### subnet

```bash
control_tools.py subnet --vpc-id <vpc-id>
```

### zones

```bash
control_tools.py zones
```

### node_specs

```bash
control_tools.py node_specs
```

### versions

Best-effort list derived from node specs; prefer this over hard-coded version guesses.

```bash
control_tools.py versions
```

## Instance mutation commands

### create

```bash
control_tools.py create \
  --name <name> \
  --version <value-from-versions> \
  --vpc-id <vpc-id> \
  --subnet-id <subnet-id> \
  --admin-password <password> \
  --master-spec <resourceSpecName> \
  [--master-count 3] \
  [--master-storage-spec <storageSpecName>] \
  [--master-storage-size <GiB>] \
  --hot-spec <resourceSpecName> \
  --hot-storage-spec <storageSpecName> \
  --hot-storage-size <GiB> \
  [--hot-count 2] \
  [--kibana-spec <resourceSpecName>] [--kibana-count 1] \
  [--charge-type PostPaid|PrePaid] \
  [--https true|false] \
  [--deletion-protection true|false] \
  [--pure-master true|false]
```

Notes:
- Use `vpc`, `subnet`, `zones`, `node_specs`, and `versions` first when values are missing.
- Present valid options to the user instead of guessing IDs or spec names.

### scale

```bash
control_tools.py scale \
  --id <instance-id> \
  --node-type <Master|Hot|Warm|Cold|Coordinator|Kibana|Other> \
  --spec-name <resourceSpecName> \
  --count <n> \
  [--storage-spec-name <storageSpecName>] \
  [--storage-size <GiB>]
```

Notes:
- Run only when the instance is `Running`.
- Scale one node type at a time.

### delete

```bash
control_tools.py delete --id <instance-id> --confirm
```

If deletion is blocked by deletion protection:

```bash
control_tools.py deletion_protection_set --id <instance-id> --enabled false
```

## Network and EIP commands

### eip_list

```bash
control_tools.py eip_list [--status Available|Attached|...]
```

### eip_allocate

```bash
control_tools.py eip_allocate \
  [--bandwidth <Mbps>] \
  [--billing-type PostPaidByTraffic|PostPaidByBandwidth|PrePaid] \
  [--name <name>] \
  [--isp BGP]
```

### eip_release

```bash
control_tools.py eip_release --allocation-id <id>
```

### public_network

```bash
control_tools.py public_network --id <id> --enable true|false [--eip-id <id>]
```

### ip_allowlist_get

```bash
control_tools.py ip_allowlist_get --id <instance-id>
```

### ip_allowlist_set

```bash
control_tools.py ip_allowlist_set --id <instance-id> --group-name <name> --ips '["1.2.3.4/32","5.6.7.0/24"]' [--type PRIVATE_ES|PUBLIC_ES]
```

Note:
- Use `--type PUBLIC_ES` for public endpoint allowlists.

## Other low-level commands

### reset_password

```bash
control_tools.py reset_password --id <instance-id> --admin-password <new-password>
```

### nodes

```bash
control_tools.py nodes --id <instance-id>
```

### plugins

```bash
control_tools.py plugins --id <instance-id>
```

### rename

```bash
control_tools.py rename --id <instance-id> --name <new-name>
```

### maintenance_set

```bash
control_tools.py maintenance_set --id <instance-id> --day "Mon,Wed" --time "02:00-06:00"
```

### deletion_protection_set

```bash
control_tools.py deletion_protection_set --id <instance-id> --enabled true|false
```

### restart_node

```bash
control_tools.py restart_node --id <instance-id> --node-id <node-id>
```

