import json
import os
from typing import Any, Dict, Optional, Tuple

import requests

DEFAULT_MCP_GATEWAY_URL = (
    "https://sd6k08f59gqcea6qe13vg.apigateway-cn-beijing.volceapi.com/mcp"
)


def _has_ark_skill_env() -> bool:
    """Check if ARK_SKILL_API_BASE and ARK_SKILL_API_KEY are both set.

    This is an internal authentication shortcut — when the runtime environment
    provides these variables the script can authenticate without requiring the
    user to configure Volcengine AK/SK.  The variables are never surfaced to
    end-users.
    """
    return bool(os.getenv("ARK_SKILL_API_BASE")) and bool(
        os.getenv("ARK_SKILL_API_KEY")
    )


def _get_skill_account_token() -> str:
    """Obtain a SKILL_ACCOUNT_TOKEN via the ARK GetSkillAuth API.

    Calls:
        GET {ARK_SKILL_API_BASE}?Version=2026-01-01&Action=GetSkillAuth
        Headers:
            Authorization: Bearer {ARK_SKILL_API_KEY}
            ServiceName: hqd

    Returns:
        The token string from response ``data`` field.

    Raises:
        RuntimeError: If the request fails or the response indicates an error.
    """
    ark_api_base = os.getenv("ARK_SKILL_API_BASE", "")
    ark_api_key = os.getenv("ARK_SKILL_API_KEY", "")

    auth_url = f"{ark_api_base}?Version=2026-01-01&Action=GetSkillAuth"
    headers = {
        "Authorization": f"Bearer {ark_api_key}",
        "ServiceName": "hqd",
    }

    resp = requests.get(auth_url, headers=headers, timeout=15, allow_redirects=True)
    resp.raise_for_status()

    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(
            f"GetSkillAuth failed: code={body.get('code')}, msg={body.get('msg')}"
        )

    token = body.get("data")
    if not token:
        raise RuntimeError("GetSkillAuth returned empty token")

    return token


def load_credentials(
    access_key: Optional[str] = None, secret_key: Optional[str] = None
) -> Tuple[str, str]:
    """Load credentials from parameters or environment variables.

    Authentication is resolved in the following order:

    1. **Internal ARK Skill mode** — if both ``ARK_SKILL_API_BASE`` and
       ``ARK_SKILL_API_KEY`` are present in the environment, a
       ``SKILL_ACCOUNT_TOKEN`` is obtained from the ARK GetSkillAuth API.
       AK/SK is **not** required in this case, so this function returns
       ``("", "")``.

    2. **Volcengine AK/SK mode** — falls back to ``VOLCENGINE_ACCESS_KEY`` /
       ``VOLCENGINE_SECRET_KEY`` (or the shorter ``VOLC_ACCESS_KEY`` /
       ``VOLC_SECRET_KEY`` aliases).

    Returns:
        A ``(access_key, secret_key)`` tuple.  Both values are empty strings
        when internal ARK Skill mode is active.

    Raises:
        ValueError: If no valid credentials are found through either mode.
    """
    # --- Internal: ARK Skill env (transparent, user does not need to know) ---
    if _has_ark_skill_env():
        return "", ""

    # --- User-facing: Volcengine AK/SK ---
    ak = (
        access_key
        or os.getenv("VOLCENGINE_ACCESS_KEY")
        or os.getenv("VOLC_ACCESS_KEY")
        or ""
    )
    sk = (
        secret_key
        or os.getenv("VOLCENGINE_SECRET_KEY")
        or os.getenv("VOLC_SECRET_KEY")
        or ""
    )

    if not ak or not sk:
        raise ValueError(
            "Missing credentials. Please set environment variables:\n"
            "  export VOLCENGINE_ACCESS_KEY='your-access-key'\n"
            "  export VOLCENGINE_SECRET_KEY='your-secret-key'\n"
            "Get your AK/SK from: https://www.volcengine.com/docs/6291/65568"
        )

    return ak, sk


def call_mcp_tool(
    *,
    url: str,
    access_key: str,
    secret_key: str,
    tool_name: str,
    arguments: Dict[str, Any],
    request_id: int = 1,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """Call an MCP tool via the MCP Gateway.

    All requests are sent to ``DEFAULT_MCP_GATEWAY_URL`` regardless of
    authentication mode.

    Authentication modes
    --------------------
    * **ARK Skill mode** (``ARK_SKILL_API_BASE`` + ``ARK_SKILL_API_KEY`` set):
      1. Calls ``GetSkillAuth`` to obtain a ``SKILL_ACCOUNT_TOKEN``.
      2. Sends the MCP request to ``url`` (= ``DEFAULT_MCP_GATEWAY_URL``)
         with header ``Skill-Account-Token: <token>``.

    * **Volcengine AK/SK mode** (fallback):
      Sends the MCP request to ``url`` with ``Volc-Access-Key`` /
      ``Volc-Secret-Key`` headers.

    Args:
        url: MCP Gateway endpoint URL (used as the target in all modes)
        access_key: Volcengine Access Key (used only in AK/SK mode)
        secret_key: Volcengine Secret Key (used only in AK/SK mode)
        tool_name: Name of the MCP tool to invoke
        arguments: Tool arguments dict
        request_id: JSON-RPC request ID
        timeout_seconds: Request timeout in seconds

    Returns:
        JSON-RPC response dict

    Raises:
        requests.HTTPError: If the HTTP request fails
        requests.Timeout: If the request times out
        RuntimeError: If GetSkillAuth fails in ARK Skill mode
    """
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    # Always use the passed url (which defaults to DEFAULT_MCP_GATEWAY_URL in
    # all callers) — both auth modes hit the same gateway.
    target_url = url

    if _has_ark_skill_env():
        # --- ARK Skill mode ---
        # Step 1: Obtain SKILL_ACCOUNT_TOKEN via GetSkillAuth
        token = _get_skill_account_token()

        # Step 2: Call MCP Gateway with the token
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Skill-Account-Token": token,
        }
    else:
        # --- Volcengine AK/SK mode ---
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Volc-Access-Key": access_key,
            "Volc-Secret-Key": secret_key,
        }

    response = requests.post(
        target_url,
        headers=headers,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def extract_tool_text(mcp_response: Dict[str, Any]) -> Optional[str]:
    """Extract text content from MCP tool response.

    Args:
        mcp_response: Raw JSON-RPC response from MCP Gateway

    Returns:
        Concatenated text content, or None if error or no text found
    """
    if "error" in mcp_response and mcp_response["error"]:
        return None

    result = mcp_response.get("result")
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            texts = []
            for item in content:
                if (
                    isinstance(item, dict)
                    and item.get("type") == "text"
                    and isinstance(item.get("text"), str)
                ):
                    texts.append(item["text"])
            if texts:
                return "\n".join(texts)

    if isinstance(result, str):
        return result

    return None


def pretty_print_mcp_result(mcp_response: Dict[str, Any]) -> None:
    """Pretty-print an MCP tool response.

    For text results, attempts JSON parsing for formatted output.
    Falls back to raw JSON-RPC dump on error or non-text responses.
    """
    if "error" in mcp_response and mcp_response["error"]:
        print(json.dumps(mcp_response, ensure_ascii=False, indent=2))
        return

    tool_text = extract_tool_text(mcp_response)
    if tool_text is None:
        print(json.dumps(mcp_response, ensure_ascii=False, indent=2))
        return

    try:
        parsed = json.loads(tool_text)
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    except Exception:
        print(tool_text)
