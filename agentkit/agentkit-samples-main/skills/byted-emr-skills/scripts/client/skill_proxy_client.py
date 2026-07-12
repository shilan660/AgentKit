import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from scripts.client.tmp_file_manager import clean_tmp_dir


def _normalize_base_url(api_host: str) -> str:
    api_host = api_host.strip()
    if api_host.startswith("http://") or api_host.startswith("https://"):
        return api_host
    # 兼容只传 host:port 的场景，默认走 https
    return f"https://{api_host}"


def _build_proxy_url(
    api_host: str,
    action: str,
    version: str,
    query: Optional[Dict[str, Any]],
) -> str:
    base = _normalize_base_url(api_host)
    parsed = urllib.parse.urlparse(base)

    # 保留用户提供的 path/port/scheme，同时合并 query
    merged_qs: Dict[str, Any] = dict(
        urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    )
    merged_qs["Action"] = action
    merged_qs["Version"] = version
    if query:
        merged_qs.update(query)

    new_query = urllib.parse.urlencode(merged_qs, doseq=True)
    return urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            "",  # fragment
        )
    )


def proxy_request(
    service: str,
    action: str,
    version: str,
    region: str,
    endpoint: str,
    method: str = "POST",
    query: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
):
    api_host = os.getenv("ARK_SKILL_API_BASE")
    api_key = os.getenv("ARK_SKILL_API_KEY")
    if not api_host or not api_key:
        raise SystemExit("缺少必要环境变量: ARK_SKILL_API_BASE, ARK_SKILL_API_KEY")

    clean_tmp_dir(hours=6)

    req_headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "ServiceName": service,
    }
    if headers:
        req_headers.update(headers)

    url = _build_proxy_url(
        api_host=api_host, action=action, version=version, query=query
    )
    logging.info("proxy_request, url=%s, body=%s, query=%s", url, body, query)
    data: Optional[bytes] = None
    if method.upper() not in {"GET", "HEAD"} and body is not None:
        data = json.dumps(body).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 返回文本（避免 bytes 直接被上层 json.dumps 时 TypeError）
            text = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                logging.error("skill proxy 响应非 JSON: %s", text)
                raise SystemExit("ARK skill proxy 响应解析失败")
    except urllib.error.URLError as e:
        logging.error(e)
        raise SystemExit(
            "请求 ARK skill proxy 失败. "
            f"api_base={api_host!r}, url={url!r}, err={e!r}. "
        )


if __name__ == "__main__":
    result = proxy_request("emr", "ListClusters", "2023-08-15", "cn-beijing", "")
    print(result)
