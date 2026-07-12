# Patterns Reference

Use this reference as a workflow index for common Elasticsearch/OpenSearch tasks. For exact request bodies, open the referenced canonical file.

## 1. Start with connectivity and engine preflight

Use when the cluster is new, credentials may be wrong, or compatibility is unknown.

1. Check `GET /`.
2. Confirm reachability, auth success, TLS success, and engine/version.
3. If that fails, use `connectivity.md` first.

Primary reference: `connectivity.md`
Secondary reference: `diagnostics.md`

## 2. Create or inspect an index

Use when the user wants to create an index, inspect mappings, update safe settings, or manage aliases.

1. If the index may already exist, check existence first.
2. For new indices, use the canonical create-index body from `index.md`.
3. For cutovers or logical renames, use aliases instead of rename-style assumptions.
4. Require explicit confirmation before delete.

Primary reference: `index.md`

## 3. Read or write one known document

Use when the user knows the target index and document ID, or wants a single-document create/update/delete.

1. Use `_doc` lookup when the ID is known.
2. Use explicit-ID index or partial update for routine writes.
3. Use upsert only when create-if-missing is intended.
4. Require explicit confirmation before delete.

Primary reference: `documents.md`

## 4. Search for matching documents

Use when the user wants matching documents rather than one known ID.

1. Inspect mappings first if field behavior is unclear.
2. Use `match`/`multi_match` for analyzed text and `term`/`terms` for exact values.
3. Add bounded filters, explicit sort, and limited `_source`.
4. Use `search_after` instead of deep paging when the user needs the next page.

Primary reference: `search.md`
Supporting references: `index.md`, `connectivity.md`

## 5. Return summaries instead of raw documents

Use when the user wants grouped counts, trends, percentiles, or rollups.

1. Prefer `size: 0`.
2. Add time filters when the data is time-based.
3. Use `.keyword` fields for exact grouping when available.
4. Keep bucket sizes bounded.

Primary reference: `aggregation.md`

## 6. Bulk ingest or broad write operations

Use when the user needs NDJSON bulk ingestion or asks for by-query/reindex-like writes.

1. Keep target indices explicit.
2. Use the canonical NDJSON structure from `write.md`.
3. Inspect per-item bulk results instead of assuming success.
4. For by-query or reindex-like changes, preview scope first and require explicit confirmation.

Primary reference: `write.md`
Supporting references: `documents.md`

## 7. Diagnose cluster-level issues safely

Use when searches time out, shard health is suspicious, or broader diagnostics are needed.

1. Start with `GET /` and `GET /_cluster/health`.
2. Use cat APIs only for visibility, not remediation.
3. Keep the workflow non-destructive unless the user explicitly asks for deeper operational changes.

Primary reference: `diagnostics.md`
Supporting reference: `connectivity.md`
