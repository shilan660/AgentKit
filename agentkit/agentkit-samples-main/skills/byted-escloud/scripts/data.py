# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def print_result(data: Any) -> None:
    print(
        json.dumps(
            {"status": "success", "data": data},
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


def print_error(msg: str, details: Optional[str] = None) -> None:
    err: Dict[str, Any] = {"error": msg}
    if details:
        err["details"] = details
    print(json.dumps(err, ensure_ascii=False))
    sys.exit(1)


def parse_endpoint(endpoint: str) -> Dict[str, Any]:
    u = urlparse(endpoint)
    if not u.scheme or not u.hostname:
        print_error(
            "Invalid Endpoint",
            "Endpoint must include scheme and host, e.g. https://domain:9200",
        )
    scheme = u.scheme.lower()
    if scheme not in ("http", "https"):
        print_error("Invalid Endpoint", "Endpoint scheme must be http or https")
    port = u.port or (443 if scheme == "https" else 80)
    return {"host": u.hostname, "port": port, "scheme": scheme}


def str_to_bool(v: str) -> bool:
    if v.lower() in ("true", "1", "yes", "y"):
        return True
    if v.lower() in ("false", "0", "no", "n"):
        return False
    raise argparse.ArgumentTypeError(f"Boolean value expected, got '{v}'")


def build_client(args):
    try:
        from opensearchpy import OpenSearch
    except Exception as e:
        print_error(
            "Missing Dependency",
            f"Failed to import opensearch-py: {str(e)}. Instruction: install dependencies with '{args.base_python} -m pip install -r requirements.txt'.",
        )

    endpoint = args.endpoint or os.environ.get("ESCLOUD_ENDPOINT", "")
    if not endpoint:
        print_error("Missing Endpoint", "Provide --endpoint or set ESCLOUD_ENDPOINT.")

    host = parse_endpoint(endpoint)

    username = args.username or os.environ.get("ESCLOUD_USERNAME", "")
    password = args.password or os.environ.get("ESCLOUD_PASSWORD", "")
    api_key = args.api_key or os.environ.get("ESCLOUD_API_KEY", "")
    bearer = args.bearer_token or os.environ.get("ESCLOUD_BEARER_TOKEN", "")

    if sum(1 for x in [(username or password), api_key, bearer] if x) > 1:
        print_error(
            "Invalid Auth",
            "Specify only one auth method: basic OR api-key OR bearer-token.",
        )
    if password and not username:
        print_error(
            "Invalid Auth",
            "When using basic auth, --username is required if --password is set.",
        )

    headers: Dict[str, str] = {}
    http_auth = None
    if username:
        http_auth = (username, password)
    if api_key:
        headers["Authorization"] = f"ApiKey {api_key}"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

    insecure_env = os.environ.get("ESCLOUD_INSECURE", "")
    insecure_default = insecure_env.lower() in ("true", "1", "yes", "y")
    insecure = args.insecure or insecure_default
    ca_certs = args.ca_certs or os.environ.get("ESCLOUD_CA_CERTS", "")

    try:
        return OpenSearch(
            hosts=[host],
            http_auth=http_auth,
            headers=headers or None,
            verify_certs=not insecure,
            ca_certs=ca_certs or None,
            timeout=args.timeout,
            http_compress=args.http_compress,
        )
    except Exception as e:
        print_error(
            "Failed to Create Client",
            f"{str(e)}. Instruction: Verify endpoint/auth/TLS options.",
        )


def preflight_info(client) -> Dict[str, Any]:
    try:
        info = client.info()
    except Exception as e:
        print_error(
            "Connectivity Check Failed",
            f"{str(e)}\n\nInstruction: Verify endpoint reachability and IP allowlist; then verify credentials.",
        )
    if not isinstance(info, dict):
        return {"raw": str(info)}
    return info


def detect_engine(info: Dict[str, Any]) -> Dict[str, str]:
    version = (info.get("version") or {}) if isinstance(info, dict) else {}
    number = str(version.get("number") or "")
    distribution = str(version.get("distribution") or "")
    engine = "opensearch" if distribution.lower() == "opensearch" else "elasticsearch"
    return {"engine": engine, "version": number or distribution or "unknown"}


def maybe_apply_es8_compat_headers(client, server: Dict[str, str]) -> None:
    if server.get("engine") != "elasticsearch":
        return
    ver = server.get("version", "")
    if not ver.startswith("8."):
        return
    headers = getattr(client.transport, "headers", None)
    if headers is None:
        return
    headers.setdefault(
        "Accept", "application/vnd.elasticsearch+json; compatible-with=7"
    )
    headers.setdefault(
        "Content-Type", "application/vnd.elasticsearch+json; compatible-with=7"
    )


def get_server(client) -> Dict[str, Any]:
    info = preflight_info(client)
    server = detect_engine(info)
    maybe_apply_es8_compat_headers(client, server)
    return {"info": info, "server": server}


def cmd_info(client, args):
    server_data = get_server(client)
    print_result(server_data)


def cmd_index_exists(client, args):
    server_data = get_server(client)
    try:
        exists = client.indices.exists(index=args.index)
    except Exception as e:
        print_error("Index Exists Failed", str(e))
    print_result(
        {"server": server_data["server"], "index": args.index, "exists": bool(exists)}
    )


def cmd_index_list(client, args):
    server_data = get_server(client)
    try:
        indices = client.cat.indices(format="json")
        print_result({"server": server_data["server"], "indices": indices})
        return
    except Exception:
        pass
    try:
        aliases = client.indices.get_alias(index="*")
        print_result(
            {"server": server_data["server"], "indices": sorted(list(aliases.keys()))}
        )
    except Exception as e:
        print_error("Index List Failed", str(e))


def cmd_index_get(client, args):
    server_data = get_server(client)
    try:
        settings = client.indices.get_settings(index=args.index)
        mappings = client.indices.get_mapping(index=args.index)
        aliases = client.indices.get_alias(index=args.index)
    except Exception as e:
        print_error("Index Get Failed", str(e))
    print_result(
        {
            "server": server_data["server"],
            "index": args.index,
            "settings": settings,
            "mappings": mappings,
            "aliases": aliases,
        }
    )


def cmd_cluster_health(client, args):
    server_data = get_server(client)
    try:
        health = client.cluster.health()
    except Exception as e:
        print_error("Cluster Health Failed", str(e))
    print_result({"server": server_data["server"], "health": health})


def cmd_cat_nodes(client, args):
    server_data = get_server(client)
    try:
        nodes = client.cat.nodes(format="json")
    except Exception as e:
        print_error("Cat Nodes Failed", str(e))
    print_result({"server": server_data["server"], "nodes": nodes})


def cmd_cat_shards(client, args):
    server_data = get_server(client)
    try:
        shards = client.cat.shards(format="json")
    except Exception as e:
        print_error("Cat Shards Failed", str(e))
    print_result({"server": server_data["server"], "shards": shards})


def build_smoke_test_doc(index_name: str) -> Dict[str, Any]:
    return {
        "source": "byted-escloud-smoke-test",
        "index_name": index_name,
        "message": "smoke test document",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def cmd_smoke_test(client, args):
    server_data = get_server(client)
    index_name = args.index or "escloud-smoke-test"
    doc_id = args.doc_id or "smoke-test-doc"
    cleanup_requested = args.cleanup

    summary: Dict[str, Any] = {
        "server": server_data["server"],
        "index": index_name,
        "doc_id": doc_id,
        "cleanup_requested": cleanup_requested,
    }

    try:
        exists_before = bool(client.indices.exists(index=index_name))
    except Exception as e:
        print_error(
            "Smoke Test Failed", f"Failed to check whether test index exists: {str(e)}"
        )
    summary["index_exists_before"] = exists_before

    if exists_before and not args.reuse_existing:
        print_error(
            "Smoke Test Refused",
            "Test index already exists. Re-run with --reuse-existing, or pass --index with a disposable name.",
        )

    if not exists_before:
        try:
            create_result = client.indices.create(
                index=index_name,
                body={
                    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                    "mappings": {
                        "properties": {
                            "source": {"type": "keyword"},
                            "index_name": {"type": "keyword"},
                            "message": {"type": "text"},
                            "created_at": {"type": "date"},
                        }
                    },
                },
            )
        except Exception as e:
            print_error(
                "Smoke Test Failed",
                f"Failed to create test index '{index_name}': {str(e)}",
            )
        summary["create_index_result"] = create_result

    doc = build_smoke_test_doc(index_name)
    try:
        index_result = client.index(index=index_name, id=doc_id, body=doc, refresh=True)
    except Exception as e:
        print_error("Smoke Test Failed", f"Failed to index sample document: {str(e)}")
    summary["index_doc_result"] = index_result

    try:
        get_result = client.get(index=index_name, id=doc_id)
    except Exception as e:
        print_error(
            "Smoke Test Failed", f"Failed to read back sample document: {str(e)}"
        )
    summary["get_doc_result"] = get_result

    try:
        search_result = client.search(
            index=index_name,
            body={
                "size": 5,
                "query": {"match": {"message": "smoke test"}},
                "sort": [{"created_at": "desc"}, {"_id": "asc"}],
                "_source": ["source", "index_name", "message", "created_at"],
            },
        )
    except Exception as e:
        print_error("Smoke Test Failed", f"Failed to search sample document: {str(e)}")
    summary["search_result"] = search_result

    cleanup_result: Dict[str, Any] = {"performed": False}
    if cleanup_requested:
        if not args.confirm:
            print_error(
                "Confirmation Required",
                "Refusing smoke-test cleanup without --confirm. Re-run with --cleanup --confirm to delete the test index.",
            )
        try:
            delete_result = client.indices.delete(index=index_name)
        except Exception as e:
            print_error(
                "Smoke Test Cleanup Failed",
                f"Failed to delete test index '{index_name}': {str(e)}",
            )
        cleanup_result = {"performed": True, "delete_index_result": delete_result}
    summary["cleanup"] = cleanup_result

    print_result(summary)


def add_common_connection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--endpoint",
        default="",
        help="Endpoint URL, e.g. https://domain:9200 (or set ESCLOUD_ENDPOINT)",
    )
    parser.add_argument(
        "--username", default="", help="Basic auth username (or set ESCLOUD_USERNAME)"
    )
    parser.add_argument(
        "--password", default="", help="Basic auth password (or set ESCLOUD_PASSWORD)"
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="API key for Authorization header (or set ESCLOUD_API_KEY)",
    )
    parser.add_argument(
        "--bearer-token",
        default="",
        help="Bearer token for Authorization header (or set ESCLOUD_BEARER_TOKEN)",
    )
    parser.add_argument(
        "--ca-certs", default="", help="Path to CA bundle (or set ESCLOUD_CA_CERTS)"
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS cert verification (or set ESCLOUD_INSECURE=true)",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Request timeout seconds (default: 30)"
    )
    parser.add_argument(
        "--http-compress",
        type=str_to_bool,
        default=True,
        help="Enable HTTP compression (default: true)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ESCloud data plane helper CLI for quickstart, smoke tests, and safe inspection"
    )
    parser.set_defaults(base_python=sys.executable)
    add_common_connection_args(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="Connectivity check and server info")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("index_exists", help="Check index existence")
    p.add_argument("--index", required=True)
    p.set_defaults(func=cmd_index_exists)

    p = sub.add_parser("index_list", help="List indices")
    p.set_defaults(func=cmd_index_list)

    p = sub.add_parser(
        "index_get", help="Get settings, mappings, and aliases for an index"
    )
    p.add_argument("--index", required=True)
    p.set_defaults(func=cmd_index_get)

    p = sub.add_parser("cluster_health", help="Get cluster health")
    p.set_defaults(func=cmd_cluster_health)

    p = sub.add_parser("cat_nodes", help="List cluster nodes via cat API")
    p.set_defaults(func=cmd_cat_nodes)

    p = sub.add_parser("cat_shards", help="List shards via cat API")
    p.set_defaults(func=cmd_cat_shards)

    p = sub.add_parser(
        "smoke_test",
        help="Create a disposable test index, index one sample doc, read it back, and optionally clean up",
    )
    p.add_argument(
        "--index",
        default="escloud-smoke-test",
        help="Disposable test index name (default: escloud-smoke-test)",
    )
    p.add_argument(
        "--doc-id",
        default="smoke-test-doc",
        help="Sample document ID (default: smoke-test-doc)",
    )
    p.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Reuse the index if it already exists",
    )
    p.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the test index after verification",
    )
    p.add_argument(
        "--confirm",
        action="store_true",
        help="Required safety flag when --cleanup is used",
    )
    p.set_defaults(func=cmd_smoke_test)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    client = build_client(args)
    args.func(client, args)


if __name__ == "__main__":
    main()
