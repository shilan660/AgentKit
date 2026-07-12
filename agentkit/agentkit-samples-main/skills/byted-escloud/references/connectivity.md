# Connectivity Reference

Use this reference for remote connection safety, authentication, TLS, privileges, and connectivity preflight.

## Default posture

- Prefer HTTPS for remote clusters.
- Prefer least-privilege credentials.
- Use explicit auth rather than assuming anonymous access.
- Treat production clusters as sensitive by default.
- Separate safe reads from routine writes and destructive writes when discussing permissions.

## Supported configuration

### Base URL

```bash
ES_URL=https://search.example.com
# or
OPENSEARCH_URL=https://search.example.com
```

### Auth

```bash
# Basic auth
ES_USERNAME=app_user
ES_PASSWORD=secret

# or API key auth
ES_API_KEY=base64-or-raw-api-key
```

### Optional CA certificate

```bash
ES_CA_CERT=/absolute/path/to/ca.crt
```

## Connectivity preflight

Use a lightweight request before broader reads or writes.

**Method / Endpoint**:
```http
GET /
```

Confirm:
- the base URL is reachable
- TLS succeeds with the expected certificate chain
- credentials are accepted
- the response reveals engine/version details that may affect later guidance

## Privilege guidance

- `_search` and `GET /<index>/_doc/<id>` usually need index read permissions.
- `_mapping`, `_settings`, `_alias`, and `_cat/*` may need broader monitor or admin-style visibility.
- document writes usually need write permissions.
- index create/delete and alias changes usually need index admin permissions.
- security plugins and managed-service policies can change exact privilege names and failure modes.

## Common auth failures

- `401 Unauthorized`: invalid credentials, rejected API key, or missing auth header.
- `403 Forbidden`: valid credentials but insufficient privileges.
- `_search` success with `_mapping` failure often means the role is too narrow.
- read operations succeeding does not imply delete or alias permissions are available.

## TLS guidance

- use `ES_CA_CERT` when the endpoint is signed by a private CA
- certificate errors often mean missing CA trust, hostname mismatch, or proxy interception
- avoid telling users to disable TLS verification unless they explicitly accept the risk
