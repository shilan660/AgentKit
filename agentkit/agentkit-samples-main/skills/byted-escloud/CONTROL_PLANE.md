# Control Plane - Goal-Based Cluster Management

Primary lifecycle guide for ESCloud operations via `control.py`; shared guardrails from [SKILL.md](SKILL.md) apply here.

## Command prefix

```bash
{baseDir}/venv/bin/python {baseDir}/scripts/control.py <command>
```

## Output contract

`control.py` returns JSON with `status`, `goal`, `data`, and `steps_completed`.

Operator rules:
- `status: success` -> continue to validation or next step.
- `status: error` -> stop immediately and report the error.
- `status: timeout` -> do not blindly rerun the same mutation; inspect current instance state first.

## Global execution rules

- Use instance ID (`--id`) for all mutating operations.
- Do not mutate instances in transitional states such as `Creating`, `Updating`, `Scaling`, or `Releasing`.
- For transitional states, wait 30-60 seconds and re-check status.
- Scale one node type at a time and wait for `Running` before the next scale.
- Enable or disable public access only when explicitly requested.

## Timeout recovery

When `status == timeout`:
1. Check `steps_completed`.
2. If the main mutation step was already sent, do not resend it immediately.
3. Inspect with `control.py detail --id <instance-id>`.
4. If the instance is still transitional, wait 30-60 seconds and check again.
5. Continue only after the instance returns to a stable state, typically `Running`.

## Workflows

### List instances

- **When**: user asks to list ESCloud instances.
- **Run**:

```bash
control.py list [--page-number <N>] [--page-size <N>]
```

- **Validate**: ensure the output includes the expected instances and pagination fields.

### Provision / create instance

- **When**: user asks to create an ESCloud instance.
- **Preconditions**: collect required inputs such as VPC, subnet, version, node specs, storage, and admin password.
- **Discover options**:

```bash
control.py provision-info
```

- **Run**:

```bash
control.py provision \
  --name <instance-name> \
  --vpc-id <vpc-id> \
  --subnet-id <subnet-id> \
  --admin-password <password> \
  --version <version> \
  --hot-spec <spec> \
  --hot-storage-spec <storage-spec> \
  --hot-storage-size <GiB> \
  [--charge-type PostPaid|PrePaid] \
  [--master-spec <spec>] [--master-count <N>] [--master-storage-spec <storage-spec>] [--master-storage-size <GiB>] \
  [--kibana-spec <spec>] [--kibana-count <N>] \
  [--poll-interval <seconds>] [--timeout <seconds>]
```

- **Validate**: confirm the command succeeds and the instance reaches `Running`.
- **Next**: optionally configure public access or IP allowlist.

### Inspect status / detail

- **When**: user asks for instance status, details, or endpoint information.
- **Run**:

```bash
control.py detail --id <instance-id>
```

- **Validate**: surface normalized status, endpoints, and any transitional state.
- **Next**: if the instance is transitional, wait before any further mutation.

### Scale instance

- **When**: user asks to change node count, node spec, or storage for one node type.
- **Preconditions**: instance must be `Running`.
- **Run**:

```bash
control.py scale --id <instance-id> \
  --node-type <Master|Hot|Kibana|...> \
  --spec-name <spec> \
  --count <N> \
  [--storage-spec-name <storage-spec>] [--storage-size <GiB>] \
  [--poll-interval <seconds>] [--timeout <seconds>]
```

- **Validate**: wait until the instance returns to `Running`.
- **Next**: if additional node types must change, repeat sequentially.

### Manage public access

- **When**: user asks to enable or disable internet access, or expose the endpoint.
- **Preconditions**: instance should be `Running`.
- **Run**:

```bash
control.py public-access --id <instance-id> --enable true|false \
  [--eip-id <eip-id>] [--eip-bandwidth <Mbps>] [--eip-billing-type <type>] [--eip-isp <isp>] [--eip-auto-reuse true|false] \
  [--poll-interval <seconds>] [--timeout <seconds>]
```

- **Validate**: confirm endpoint/EIP state in status output.
- **Next**: if enabling public access, configure public IP allowlist before data-plane operations.

- Prefer reusing an existing available EIP before allocating a new one.
- After public endpoint changes, update allowlists before data-plane work.

### Manage IP allowlist

- **When**: user asks to permit client IPs for private or public access.
- **Preconditions**: identify the correct allowlist type for the target endpoint.
- **Run**:

```bash
control.py allowlist --id <instance-id> \
  --ips "<ip1>,<ip2>" \
  [--group-name <name>] [--type PRIVATE_ES|PUBLIC_ES] \
  [--poll-interval <seconds>] [--timeout <seconds>]
```

- **Validate**: confirm the instance returns to `Running` and the allowlist reflects the requested IP set.
- **Next**: retry connectivity checks if this was done to unblock data-plane access.

### Reset admin password

- **When**: user asks to rotate or reset the admin password.
- **Preconditions**: instance should be `Running`.
- **Run**:

```bash
control.py reset-password --id <instance-id> --admin-password <password> \
  [--poll-interval <seconds>] [--timeout <seconds>]
```

- **Validate**: wait until the instance returns to `Running`.
- **Next**: if the password was needed for data-plane access, retry endpoint connectivity.

### Maintenance window

- **When**: user asks to set maintenance days or time ranges.
- **Run**:

```bash
control.py maintenance --id <instance-id> --day "Mon,Wed" --time "02:00-06:00"
```

- **Validate**: confirm the new maintenance policy in follow-up status/detail output.

### Rename instance

- **When**: user asks to rename the instance.
- **Run**:

```bash
control.py rename --id <instance-id> --name <new-name>
```

- **Validate**: confirm the updated name from status/detail output.

### Restart node

- **When**: user asks to restart a specific node.
- **Preconditions**: identify the exact target node.
- **Run**:

```bash
control.py restart-node --id <instance-id> --node-id <node-id> [--force] \
  [--poll-interval <seconds>] [--timeout <seconds>]
```

- **Validate**: wait until the instance returns to `Running`.

### Delete / deprovision instance

- **When**: user asks to delete an instance.
- **Preconditions**: show the exact target name and ID; require explicit user confirmation before executing.
- **Run**:

```bash
control.py deprovision --id <instance-id> --confirm <instance-id> [--force] \
  [--poll-interval <seconds>] [--timeout <seconds>]
```

- **Validate**: stop on error; if deletion protection blocks the action, rerun with the supported force option.
- **Next**: none.
