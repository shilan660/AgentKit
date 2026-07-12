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
from abc import ABC, abstractmethod
from typing import Any


class ApiError(Exception):
    pass


class EsCloudApi(ABC):
    @abstractmethod
    def _call(self, method: str, action: str, body: Any) -> Any:
        pass

    def describe_instances(self, body: Any) -> Any:
        return self._call("POST", "DescribeInstances", body)

    def describe_instance(self, body: Any) -> Any:
        return self._call("POST", "DescribeInstance", body)

    def describe_zones(self, body: Any) -> Any:
        return self._call("POST", "DescribeZones", body)

    def describe_node_available_specs(self, body: Any) -> Any:
        return self._call("POST", "DescribeNodeAvailableSpecs", body)

    def create_instance_in_one_step(self, body: Any) -> Any:
        return self._call("POST", "CreateInstanceInOneStep", body)

    def modify_node_spec_in_one_step(self, body: Any) -> Any:
        return self._call("POST", "ModifyNodeSpecInOneStep", body)

    def release_instance(self, body: Any) -> Any:
        return self._call("POST", "ReleaseInstance", body)

    def describe_ip_allow_list(self, body: Any) -> Any:
        return self._call("POST", "DescribeIpAllowList", body)

    def modify_ip_allow_list_v2(self, body: Any) -> Any:
        return self._call("POST", "ModifyIpAllowListV2", body)

    def reset_admin_password(self, body: Any) -> Any:
        return self._call("POST", "ResetAdminPassword", body)

    def describe_instance_nodes(self, body: Any) -> Any:
        return self._call("POST", "DescribeInstanceNodes", body)

    def describe_instance_plugins(self, body: Any) -> Any:
        return self._call("POST", "DescribeInstancePlugins", body)

    def rename_instance(self, body: Any) -> Any:
        return self._call("POST", "RenameInstance", body)

    def modify_maintenance_setting(self, body: Any) -> Any:
        return self._call("POST", "ModifyMaintenanceSetting", body)

    def modify_deletion_protection(self, body: Any) -> Any:
        return self._call("POST", "ModifyDeletionProtection", body)

    def restart_node(self, body: Any) -> Any:
        return self._call("POST", "RestartNode", body)

    def create_public_address(self, body: Any) -> Any:
        return self._call("POST", "CreatePublicAddress", body)

    def release_public_address(self, body: Any) -> Any:
        return self._call("POST", "ReleasePublicAddress", body)


class VpcApi(ABC):
    @abstractmethod
    def _call(self, method: str, action: str, body: Any) -> Any:
        pass

    def describe_vpcs(self, body: Any) -> Any:
        return self._call("GET", "DescribeVpcs", body)

    def describe_subnets(self, body: Any) -> Any:
        return self._call("GET", "DescribeSubnets", body)

    def describe_eip_addresses(self, body: Any) -> Any:
        return self._call("GET", "DescribeEipAddresses", body)

    def allocate_eip_address(self, body: Any) -> Any:
        return self._call("GET", "AllocateEipAddress", body)

    def release_eip_address(self, body: Any) -> Any:
        return self._call("GET", "ReleaseEipAddress", body)
