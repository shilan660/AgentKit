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
from typing import Any, Dict

import volcenginesdkcore
from volcenginesdkcore.universal import UniversalApi, UniversalInfo
from volcenginesdkcore.rest import ApiException

from api import ApiError, EsCloudApi, VpcApi


class _SimpleResponse:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return self._payload


class _UniversalShim:
    def __init__(self):
        ak = os.environ.get("VOLCENGINE_ACCESS_KEY")
        sk = os.environ.get("VOLCENGINE_SECRET_KEY")
        region = os.environ.get("VOLCENGINE_REGION", "cn-beijing")

        if not ak or not sk:
            raise ApiError(
                "Missing Credentials: VOLCENGINE_ACCESS_KEY or VOLCENGINE_SECRET_KEY is not set. "
                "Ask the user to provide their Volcano Engine Access Key and Secret Key."
            )

        configuration = volcenginesdkcore.Configuration()
        configuration.ak = ak
        configuration.sk = sk
        configuration.region = region
        configuration.client_side_validation = False

        self._api = UniversalApi(volcenginesdkcore.ApiClient(configuration))
        self.region = region

    def do_call(
        self, service: str, action: str, version: str, method: str, body: Any
    ) -> Dict[str, Any]:
        info = UniversalInfo(
            method=method.upper(), service=service, version=version, action=action
        )
        if method.upper() != "GET":
            info.content_type = "application/json"
        try:
            resp = self._api.do_call(info, body)
            if isinstance(resp, dict):
                return resp
            if hasattr(resp, "to_dict"):
                return resp.to_dict()
            return {"Result": resp}
        except ApiException as exc:
            raise ApiError(str(exc))
        except Exception as exc:
            raise ApiError(f"SDK Error: {str(exc)}")


class ESCloudSdkShim(EsCloudApi):
    def __init__(self, bridge: _UniversalShim):
        self._bridge = bridge

    def _call(self, method: str, action: str, body: Any) -> Any:
        payload = body.to_dict() if hasattr(body, "to_dict") else (body or {})
        return _SimpleResponse(
            self._bridge.do_call("ESCloud", action, "2023-01-01", method, payload)
        )


class VpcSdkShim(VpcApi):
    def __init__(self, bridge: _UniversalShim):
        self._bridge = bridge

    def _call(self, method: str, action: str, body: Any) -> Any:
        payload = body.to_dict() if hasattr(body, "to_dict") else (body or {})
        return _SimpleResponse(
            self._bridge.do_call("vpc", action, "2020-04-01", method, payload)
        )


def get_clients():
    try:
        bridge = _UniversalShim()
        return ESCloudSdkShim(bridge), VpcSdkShim(bridge), None, bridge.region
    except ApiError as exc:
        print(
            json.dumps(
                {"error": "Initialization Error", "details": str(exc)},
                ensure_ascii=False,
            )
        )
        sys.exit(1)
