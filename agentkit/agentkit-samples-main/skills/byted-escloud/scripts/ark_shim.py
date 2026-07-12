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
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict


from api import ApiError, EsCloudApi, VpcApi


class _SimpleResponse:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return self._payload


api_host = os.environ.get("ARK_SKILL_API_BASE")
api_key = os.environ.get("ARK_SKILL_API_KEY")


def check_is_ark_env() -> bool:
    return bool(api_host and api_key)


def _do_http_call(
    service_name: str,
    action: str,
    version: str,
    method: str,
    body_dict: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if not check_is_ark_env():
        raise ApiError(
            "ARK_SKILL_API_BASE and ARK_SKILL_API_KEY must be set for ark_shim"
        )

    url = f"{api_host.rstrip('/')}/?Action={action}&Version={version}"
    headers = {
        "ServiceName": service_name,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    if method.upper() == "GET":
        if body_dict:
            query = urllib.parse.urlencode(body_dict, doseq=True)
            url = f"{url}&{query}"
        data = None
    else:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body_dict or {}).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise ApiError(f"HTTP {exc.code}: {exc.reason} - {error_body}")
    except Exception as exc:
        raise ApiError(f"Network error: {str(exc)}")


class ESCloudHttpShim(EsCloudApi):
    def _call(self, method: str, action: str, body: Any) -> Any:
        payload = body.to_dict() if hasattr(body, "to_dict") else (body or {})
        return _SimpleResponse(
            _do_http_call("ESCloud", action, "2023-01-01", method, payload)
        )


class VpcHttpShim(VpcApi):
    def _call(self, method: str, action: str, body: Any) -> Any:
        payload = body.to_dict() if hasattr(body, "to_dict") else (body or {})
        return _SimpleResponse(
            _do_http_call("vpc", action, "2020-04-01", method, payload)
        )


def get_clients():
    try:
        region = os.environ.get("VOLCENGINE_REGION", "cn-beijing")
        return ESCloudHttpShim(), VpcHttpShim(), None, region
    except ApiError as exc:
        print(
            json.dumps(
                {"error": "Initialization Error", "details": str(exc)},
                ensure_ascii=False,
            )
        )
        sys.exit(1)
