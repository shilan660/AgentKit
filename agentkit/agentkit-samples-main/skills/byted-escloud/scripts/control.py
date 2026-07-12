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
import sys
import time
from typing import Any, Callable, Tuple
from api import ApiError, EsCloudApi, VpcApi

# EIP Billing Types mapping (human strings to API integers)
EIP_BILLING_TYPES = {
    "PrePaid": 1,
    "PostPaid": 2,  # Postpaid by Bandwidth
    "PostPaidByTraffic": 3,  # Postpaid by Traffic (Recommended)
}


class WorkflowError(Exception):
    def __init__(
        self,
        error: str,
        details: str = "",
        data: dict[str, Any] | None = None,
        steps_completed: list[str] | None = None,
    ):
        super().__init__(details or error)
        self.error = error
        self.details = details
        self.data = data or {}
        self.steps_completed = list(steps_completed or [])


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, default=str, ensure_ascii=False))
    sys.exit(exit_code)


def first_present(obj: Any, keys: list[str]) -> Any:
    if isinstance(obj, dict):
        for key in keys:
            if key in obj and obj[key] not in (None, ""):
                return obj[key]
        for value in obj.values():
            found = first_present(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = first_present(item, keys)
            if found not in (None, ""):
                return found
    return None


def get_list(obj: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, list):
            return value
    result = obj.get("Result") or obj.get("result")
    if isinstance(result, dict):
        for key in keys:
            value = result.get(key)
            if isinstance(value, list):
                return value
    return []


def normalize_detail(detail: dict[str, Any]) -> dict[str, Any]:
    result = detail.get("Result") or detail.get("result") or detail
    inst_id = first_present(result, ["InstanceId", "instance_id", "Id", "id"])

    inst_conf = result.get("InstanceConfiguration", {})
    name = first_present(inst_conf, ["InstanceName", "instance_name"])

    status = first_present(result, ["Status", "status"])
    return {
        "id": inst_id,
        "name": name,
        "status": status,
        "raw": detail,
    }


def str_to_bool(v: str) -> bool:
    if isinstance(v, bool):
        return v
    if v.lower() in ("true", "1", "yes", "y"):
        return True
    if v.lower() in ("false", "0", "no", "n"):
        return False
    raise argparse.ArgumentTypeError(f"Boolean value expected, got '{v}'")


def add_eip_alloc_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--eip-id", default="", help="Existing EIP allocation id")
    parser.add_argument(
        "--eip-bandwidth",
        type=int,
        default=10,
        help="EIP bandwidth for auto-allocation",
    )
    parser.add_argument(
        "--eip-billing-type",
        type=str,
        default="PostPaidByTraffic",
        choices=list(EIP_BILLING_TYPES.keys()),
        help=f"EIP billing type for auto-allocation (Allowed: {', '.join(EIP_BILLING_TYPES.keys())})",
    )
    parser.add_argument("--eip-isp", type=str, default="BGP", help="Optional EIP ISP")
    parser.add_argument(
        "--eip-auto-reuse",
        type=str_to_bool,
        default=True,
        help="If true, reuse an existing Available EIP before allocating a new one",
    )


def _get_clients() -> Tuple[EsCloudApi, VpcApi, Any, str]:
    import ark_shim

    if ark_shim.check_is_ark_env():
        return ark_shim.get_clients()
    import sdk_shim

    return sdk_shim.get_clients()


class ControlPlane:
    def __init__(self, debug: bool = False):
        self.es_api, self.vpc_api, self.configuration, self.region = _get_clients()
        self.debug = debug

    def _run_api(
        self, fn: Callable[[], Any], context_data: dict[str, Any] | None = None
    ) -> Any:
        try:
            resp = fn()

            # Normalize to dict for inspection
            data = resp
            try:
                if hasattr(resp, "to_dict"):
                    data = resp.to_dict()
            except Exception:
                pass

            # check for nested errors even if no exception was raised
            if isinstance(data, dict):
                error_msg = self._extract_error(data)
                if error_msg:
                    if not self.debug:
                        # Strip duplicated Error blocks from the raw response to keep output concise
                        if "Result" in data and isinstance(data["Result"], dict):
                            data["Result"].pop("Error", None)
                        if "ResponseMetadata" in data and isinstance(
                            data["ResponseMetadata"], dict
                        ):
                            data["ResponseMetadata"].pop("Error", None)
                    raise WorkflowError("API Error", error_msg, {"response": data})

            return data
        except WorkflowError:
            raise
        except ApiError as exc:
            msg = str(exc)
            if not self.debug:
                # Try to extract a more precise message from the exception string if it contains JSON
                extracted = self._extract_error(msg)
                msg = extracted if extracted else msg

            instruction = ""
            if "TaskIsRunning" in msg:
                instruction = (
                    "An operation is already in progress for this instance. "
                    "Wait for the instance to return to Running and retry."
                )
            elif any(
                key in msg
                for key in [
                    "BadRequest",
                    "InvalidParameter",
                    "NotFound",
                    "Unauthorized",
                    "InvalidAction",
                ]
            ):
                instruction = (
                    "Verify that all IDs and parameters are valid and that the current credentials "
                    "have access to the target VPC, subnet, and instance."
                )
            details = f"{msg}\n\nInstruction: {instruction}" if instruction else msg
            error_data = context_data if self.debug else None
            raise WorkflowError("API Error", details, error_data)
        except Exception as exc:
            error_data = context_data if self.debug else None
            raise WorkflowError(
                "Unexpected Error",
                f"{exc}\n\nInstruction: Internal script error. Check credentials, network, and parameters.",
                error_data,
            )

    def _extract_error(self, source: Any) -> str | None:
        """Parses API response or error string for a precise root cause message."""
        if not source:
            return None

        data = source
        if isinstance(source, str):
            try:
                # Some ApiError messages contain the JSON response
                start = source.find("{")
                end = source.rfind("}")
                if start != -1 and end != -1:
                    data = json.loads(source[start : end + 1])
                else:
                    return None
            except Exception:
                return None

        if not isinstance(data, dict):
            return None

        # Target locations for Volcengine ESCloud errors
        # 1. Result.Error
        # 2. ResponseMetadata.Error
        res_err = (
            data.get("Result", {}).get("Error", {})
            if isinstance(data.get("Result"), dict)
            else {}
        )
        meta_err = (
            data.get("ResponseMetadata", {}).get("Error", {})
            if isinstance(data.get("ResponseMetadata"), dict)
            else {}
        )

        raw_msg = res_err.get("Message") or meta_err.get("Message")
        if not raw_msg:
            return None

        # Keep original message without cropping details
        return raw_msg

    def _success(
        self, goal: str, data: dict[str, Any], steps_completed: list[str]
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "goal": goal,
            "data": data,
            "steps_completed": steps_completed,
        }

    def _error(
        self,
        goal: str,
        error: str,
        details: str,
        steps_completed: list[str],
        data: dict[str, Any] | None = None,
        status: str = "error",
    ) -> dict[str, Any]:
        error_label = error
        details_label = details
        if error_label in ("API Error", "Unexpected Error") and details_label:
            error_label = details_label
            details_label = ""

        payload = {
            "status": status,
            "goal": goal,
            "error": error_label,
        }
        if details_label:
            payload["details"] = details_label

        payload["data"] = data or {}
        payload["steps_completed"] = steps_completed
        return payload

    def _fetch_detail(self, instance_id: str) -> dict[str, Any]:
        body = {"InstanceId": instance_id}
        return self._run_api(
            lambda: self.es_api.describe_instance(body), {"instance_id": instance_id}
        )

    def _wait_for_condition(
        self,
        fetch_fn: Callable[[], dict[str, Any]],
        condition_fn: Callable[[dict[str, Any]], bool],
        poll_interval: int,
        timeout: int,
        consecutive_successes: int = 1,
    ) -> tuple[bool, dict[str, Any]]:
        deadline = time.time() + timeout
        last_detail: dict[str, Any] = {}
        success_count = 0
        while True:
            last_detail = fetch_fn()

            if condition_fn(last_detail):
                success_count += 1
                if success_count >= consecutive_successes:
                    return True, last_detail
            else:
                success_count = 0
            if time.time() >= deadline:
                return False, last_detail
            time.sleep(poll_interval)

    def detail(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        detail = self._fetch_detail(args.id)
        steps.append("fetch_detail")
        normalized = normalize_detail(detail)
        return self._success(
            "detail",
            {
                "instance_id": normalized["id"],
                "instance_name": normalized["name"],
                "status": normalized["status"],
                "detail": detail,
            },
            steps,
        )

    def list(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        body = {"PageNumber": args.page_number, "PageSize": args.page_size}
        instances = self._run_api(
            lambda: self.es_api.describe_instances(body), {"request": body}
        )
        steps.append("fetch_instances")
        return self._success("list", instances, steps)

    def provision_info(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        vpcs_resp = self._run_api(lambda: self.vpc_api.describe_vpcs({}))
        steps.append("fetch_vpcs")

        specs_resp = self._run_api(
            lambda: self.es_api.describe_node_available_specs({})
        )
        steps.append("fetch_specs")

        subnets_by_vpc: dict[str, Any] = {}
        for vpc in get_list(vpcs_resp, "Vpcs", "vpcs"):
            vpc_id = vpc.get("VpcId") or vpc.get("vpc_id")
            if not vpc_id:
                continue
            subnet_resp = self._run_api(
                lambda: self.vpc_api.describe_subnets({"VpcId": vpc_id}),
                {"vpc_id": vpc_id},
            )
            subnets_by_vpc[vpc_id] = subnet_resp
        steps.append("fetch_subnets")

        zones_resp = self._run_api(lambda: self.es_api.describe_zones({}))
        steps.append("fetch_zones")

        return self._success(
            "provision-info",
            {
                "region": self.region,
                "vpcs": vpcs_resp,
                "subnets_by_vpc": subnets_by_vpc,
                "specs": specs_resp,
                "zones": zones_resp,
            },
            steps,
        )

    def provision(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        subnet_resp = self._run_api(
            lambda: self.vpc_api.describe_subnets({"SubnetIds": [args.subnet_id]}),
            {"subnet_id": args.subnet_id},
        )
        subnets = get_list(subnet_resp, "Subnets", "subnets")
        if not subnets:
            raise WorkflowError(
                "Subnet Not Found",
                f"Subnet ID '{args.subnet_id}' does not exist or is not in the current region.",
                steps_completed=steps,
            )
        zone_id = subnets[0].get("ZoneId") or subnets[0].get("zone_id")
        if not zone_id:
            raise WorkflowError(
                "Zone Not Found",
                "Failed to derive zone_id from the subnet.",
                steps_completed=steps,
            )
        steps.append("validate_subnet")

        node_specs = []
        if args.master_spec:
            node_specs.append(
                {
                    "Type": "Master",
                    "Number": args.master_count,
                    "ResourceSpecName": args.master_spec,
                    "StorageSpecName": args.master_storage_spec
                    or args.hot_storage_spec,
                    "StorageSize": args.master_storage_size or 20,
                }
            )

        node_specs.append(
            {
                "Type": "Hot",
                "Number": args.hot_count,
                "ResourceSpecName": args.hot_spec,
                "StorageSpecName": args.hot_storage_spec,
                "StorageSize": args.hot_storage_size,
            }
        )

        if getattr(args, "kibana_spec", ""):
            node_specs.append(
                {
                    "Type": "Kibana",
                    "Number": getattr(args, "kibana_count", 1),
                    "ResourceSpecName": getattr(args, "kibana_spec", ""),
                }
            )

        instance_conf = {
            "InstanceName": args.name,
            "Version": args.version,
            "AdminPassword": args.admin_password,
            "ChargeType": args.charge_type,
            "DeletionProtection": True,
            "EnableHttps": True,
            "EnablePureMaster": True if args.master_spec else False,
            "ProjectName": "default",
            "RegionId": self.region,
            "ZoneId": zone_id,
            "VPC": {"VpcId": args.vpc_id},
            "Subnet": {"SubnetId": args.subnet_id},
            "NodeSpecsAssigns": node_specs,
        }

        body = {"InstanceConfiguration": instance_conf}
        create_resp = self._run_api(
            lambda: self.es_api.create_instance_in_one_step(body), {"request": body}
        )
        steps.append("create_instance")

        instance_id = first_present(create_resp, ["InstanceId", "instance_id", "Id"])
        if not instance_id:
            # This should normally be caught by _run_api now, but keeping a fallback
            raise WorkflowError(
                "API Error",
                "CreateInstanceInOneStep returned no instance identifier.",
                {"create_response": create_resp},
                steps_completed=steps,
            )

        ok, detail = self._wait_for_condition(
            fetch_fn=lambda: self._fetch_detail(instance_id),
            condition_fn=lambda d: normalize_detail(d)["status"] == "Running",
            poll_interval=args.poll_interval,
            timeout=args.timeout,
            consecutive_successes=2,
        )
        steps.append("poll_status")

        data = {
            "instance_id": instance_id,
            "create_response": create_resp,
            "final_detail": detail,
        }
        if ok:
            return self._success("provision", data, steps)
        return self._error(
            "provision",
            "Timeout",
            f"Instance '{instance_id}' did not reach Running within {args.timeout} seconds.",
            steps,
            data,
            status="timeout",
        )

    def deprovision(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        if args.confirm != args.id:
            raise WorkflowError(
                "Confirmation required",
                f"--confirm must exactly match the instance id {args.id!r}.",
                steps_completed=steps,
            )

        detail = self._fetch_detail(args.id)
        steps.append("fetch_detail")

        inst_info = detail.get("Result", detail).get("InstanceInfo", {})
        if inst_info.get("DeletionProtection"):
            if not getattr(args, "force", False):
                raise WorkflowError(
                    "Deletion Protection Enabled",
                    "Instance has deletion protection. Use --force to disable it and delete.",
                    steps_completed=steps,
                )
            self._run_api(
                lambda: self.es_api.modify_deletion_protection(
                    {"InstanceId": args.id, "DeletionProtection": False}
                ),
                {"instance_id": args.id},
            )
            steps.append("disable_deletion_protection")

        release_resp = self._run_api(
            lambda: self.es_api.release_instance({"InstanceId": args.id}),
            {"instance_id": args.id},
        )
        steps.append("release_instance")

        def _fetch_safe():
            try:
                return self._fetch_detail(args.id)
            except WorkflowError as e:
                if (
                    "NotFound" in str(e)
                    or "not exist" in str(e).lower()
                    or "InvalidParameter" in str(e)
                ):
                    return {"is_deleted": True}
                raise e

        ok, detail_after = self._wait_for_condition(
            fetch_fn=_fetch_safe,
            condition_fn=lambda d: d.get("is_deleted")
            or normalize_detail(d).get("status") == "Deleted",
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        steps.append("poll_deletion")

        data = {
            "instance_id": args.id,
            "release_response": release_resp,
            "final_detail": detail_after,
        }
        if ok:
            return self._success("deprovision", data, steps)
        return self._error(
            "deprovision", "Timeout", "Instance was not deleted in time.", steps, data
        )

    def scale(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        current_detail = self._fetch_detail(args.id)
        steps.append("fetch_detail")

        current_status = normalize_detail(current_detail).get("status")
        if current_status != "Running":
            raise WorkflowError(
                "Invalid Instance State",
                f"Instance '{args.id}' must be Running before scaling. Current status: {current_status!r}.",
                {"detail": current_detail},
                steps_completed=steps,
            )
        steps.append("validate_running")

        assign_kwargs = {
            "Type": args.node_type,
            "Number": args.count,
            "ResourceSpecName": args.spec_name,
        }
        if args.storage_spec_name:
            assign_kwargs["StorageSpecName"] = args.storage_spec_name
        if args.storage_size is not None:
            assign_kwargs["StorageSize"] = args.storage_size

        body = {"InstanceId": args.id, "NodeSpecsAssigns": [assign_kwargs]}
        scale_resp = self._run_api(
            lambda: self.es_api.modify_node_spec_in_one_step(body), {"request": body}
        )
        steps.append("scale_instance")

        ok, detail = self._wait_for_condition(
            fetch_fn=lambda: self._fetch_detail(args.id),
            condition_fn=lambda d: normalize_detail(d).get("status") == "Running",
            poll_interval=args.poll_interval,
            timeout=args.timeout,
            consecutive_successes=2,
        )
        steps.append("poll_status")

        data = {
            "instance_id": args.id,
            "scale_response": scale_resp,
            "final_detail": detail,
        }
        if ok:
            return self._success("scale", data, steps)
        return self._error(
            "scale",
            "Timeout",
            f"Instance '{args.id}' did not return to Running within {args.timeout} seconds.",
            steps,
            data,
            status="timeout",
        )

    def public_access(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        detail_before = self._fetch_detail(args.id)
        steps.append("fetch_detail")

        current_status = normalize_detail(detail_before).get("status")
        if current_status != "Running":
            raise WorkflowError(
                "Invalid Instance State",
                f"Instance '{args.id}' must be Running before managing public endpoint.",
                {"detail": detail_before},
                steps_completed=steps,
            )

        body = {
            "InstanceId": args.id,
        }

        if args.enable:
            eip_id = self._ensure_eip(args)
            body["EsEip"] = {"IsOpen": True, "EipId": eip_id}
            steps.append("ensure_eip")
            modify_resp = self._run_api(
                lambda: self.es_api.create_public_address(body), {"request": body}
            )
            steps.append("create_public_address")
        else:
            body["EsEip"] = {"IsOpen": False}
            modify_resp = self._run_api(
                lambda: self.es_api.release_public_address(body), {"request": body}
            )
            steps.append("release_public_address")

        ok, detail_after = self._wait_for_condition(
            fetch_fn=lambda: self._fetch_detail(args.id),
            condition_fn=lambda d: normalize_detail(d).get("status") == "Running",
            poll_interval=args.poll_interval,
            timeout=args.timeout,
            consecutive_successes=2,
        )
        steps.append("poll_endpoint")

        data = {
            "instance_id": args.id,
            "enable": args.enable,
            "modify_response": modify_resp,
            "detail_before": detail_before,
            "detail_after": detail_after,
        }
        if ok:
            return self._success("public-access", data, steps)
        return self._error(
            "public-access",
            "Timeout",
            "Endpoint change did not complete in time.",
            steps,
            data,
            status="timeout",
        )

    def allowlist(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        detail_before = self._fetch_detail(args.id)
        steps.append("fetch_detail")

        current_status = normalize_detail(detail_before).get("status")
        if current_status != "Running":
            raise WorkflowError(
                "Invalid Instance State",
                f"Instance '{args.id}' must be Running before modifying allowlist.",
                {"detail": detail_before},
                steps_completed=steps,
            )

        ips_list = args.ips.split(",") if args.ips else []
        ips_list = [ip.strip() for ip in ips_list if ip.strip()]

        allowlist_type = (args.type or "PRIVATE_ES").strip().upper()
        group = {
            "Name": args.group_name,
            "AllowList": ",".join(ips_list),
        }
        allowlist_conf = {
            "Groups": [group],
            "Type": allowlist_type,
            "AllowList": "",
        }
        body = {
            "InstanceId": args.id,
            "EsIpAllowList": allowlist_conf,
        }

        modify_resp = self._run_api(
            lambda: self.es_api.modify_ip_allow_list_v2(body), {"request": body}
        )
        steps.append("modify_allowlist")

        ok, detail_after = self._wait_for_condition(
            fetch_fn=lambda: self._fetch_detail(args.id),
            condition_fn=lambda d: normalize_detail(d).get("status") == "Running",
            poll_interval=args.poll_interval,
            timeout=args.timeout,
            consecutive_successes=2,
        )
        steps.append("poll_status")

        data = {
            "instance_id": args.id,
            "modify_response": modify_resp,
            "detail_after": detail_after,
        }
        if ok:
            return self._success("allowlist", data, steps)
        return self._error(
            "allowlist",
            "Timeout",
            "Allowlist change did not complete in time.",
            steps,
            data,
            status="timeout",
        )

    def reset_password(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        detail_before = self._fetch_detail(args.id)
        steps.append("fetch_detail")

        current_status = normalize_detail(detail_before).get("status")
        if current_status != "Running":
            raise WorkflowError(
                "Invalid Instance State",
                f"Instance '{args.id}' must be Running before resetting password.",
                {"detail": detail_before},
                steps_completed=steps,
            )

        body = {
            "InstanceId": args.id,
            "NewPassword": args.admin_password,
        }

        modify_resp = self._run_api(
            lambda: self.es_api.reset_admin_password(body), {"request": body}
        )
        steps.append("reset_password")

        ok, detail_after = self._wait_for_condition(
            fetch_fn=lambda: self._fetch_detail(args.id),
            condition_fn=lambda d: normalize_detail(d).get("status") == "Running",
            poll_interval=args.poll_interval,
            timeout=args.timeout,
            consecutive_successes=2,
        )
        steps.append("poll_status")

        data = {
            "instance_id": args.id,
            "modify_response": modify_resp,
            "detail_after": detail_after,
        }
        if ok:
            return self._success("reset-password", data, steps)
        return self._error(
            "reset-password",
            "Timeout",
            "Password reset did not complete in time.",
            steps,
            data,
            status="timeout",
        )

    def _ensure_eip(self, args: argparse.Namespace) -> str:
        if args.eip_id:
            return args.eip_id

        if args.eip_auto_reuse:
            try:
                resp = self._run_api(
                    lambda: self.vpc_api.describe_eip_addresses({"Status": "Available"})
                )
                eips = get_list(resp, "EipAddresses", "eip_addresses")
                for eip in eips:
                    alloc_id = eip.get("AllocationId") or eip.get("allocation_id")
                    if alloc_id and eip.get("Status") == "Available":
                        return alloc_id
            except Exception:
                pass

        # Allocate new EIP
        billing_type = EIP_BILLING_TYPES.get(args.eip_billing_type, 3)
        body = {
            "Bandwidth": args.eip_bandwidth,
            "BillingType": billing_type,
            "ISP": args.eip_isp or "BGP",
        }
        alloc_resp = self._run_api(
            lambda: self.vpc_api.allocate_eip_address(body), {"request": body}
        )
        eip_id = first_present(alloc_resp, ["AllocationId", "allocation_id"])
        if not eip_id:
            raise WorkflowError(
                "API Error",
                f"AllocateEipAddress returned no AllocationId: {alloc_resp!r}",
            )
        return eip_id

    def maintenance(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []

        maintenance_day = args.day
        maintenance_time = args.time
        if not maintenance_time:
            raise WorkflowError(
                "Missing Parameters", "Provide --time.", steps_completed=steps
            )

        day_map = {
            "MON": "MONDAY",
            "MONDAY": "MONDAY",
            "TUE": "TUESDAY",
            "TUES": "TUESDAY",
            "TUESDAY": "TUESDAY",
            "WED": "WEDNESDAY",
            "WEDNESDAY": "WEDNESDAY",
            "THU": "THURSDAY",
            "THUR": "THURSDAY",
            "THURS": "THURSDAY",
            "THURSDAY": "THURSDAY",
            "FRI": "FRIDAY",
            "FRIDAY": "FRIDAY",
            "SAT": "SATURDAY",
            "SATURDAY": "SATURDAY",
            "SUN": "SUNDAY",
            "SUNDAY": "SUNDAY",
        }
        raw_days = [d.strip().upper() for d in maintenance_day.split(",") if d.strip()]
        maintenance_day_parsed = [day_map.get(d, d) for d in raw_days]

        body = {
            "InstanceId": args.id,
            "MaintenanceDay": maintenance_day_parsed,
            "MaintenanceTime": maintenance_time,
        }
        modify_resp = self._run_api(
            lambda: self.es_api.modify_maintenance_setting(body), {"request": body}
        )
        steps.append("modify_maintenance")

        data = {"instance_id": args.id, "modify_response": modify_resp}
        return self._success("maintenance", data, steps)

    def rename(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        body = {"InstanceId": args.id, "NewName": args.name}
        modify_resp = self._run_api(
            lambda: self.es_api.rename_instance(body), {"request": body}
        )
        steps.append("rename_instance")

        data = {"instance_id": args.id, "modify_response": modify_resp}
        return self._success("rename", data, steps)

    def restart_node(self, args: argparse.Namespace) -> dict[str, Any]:
        steps: list[str] = []
        detail_before = self._fetch_detail(args.id)
        steps.append("fetch_detail")

        current_status = normalize_detail(detail_before).get("status")
        if current_status != "Running":
            raise WorkflowError(
                "Invalid Instance State",
                f"Instance '{args.id}' must be Running before restarting nodes.",
                {"detail": detail_before},
                steps_completed=steps,
            )

        body = {
            "InstanceId": args.id,
            "NodeName": args.node_id,
            "Force": args.force,
        }
        modify_resp = self._run_api(
            lambda: self.es_api.restart_node(body), {"request": body}
        )
        steps.append("restart_node")

        ok, detail_after = self._wait_for_condition(
            fetch_fn=lambda: self._fetch_detail(args.id),
            condition_fn=lambda d: normalize_detail(d).get("status") == "Running",
            poll_interval=args.poll_interval,
            timeout=args.timeout,
            consecutive_successes=2,
        )
        steps.append("poll_status")

        data = {
            "instance_id": args.id,
            "modify_response": modify_resp,
            "detail_after": detail_after,
        }
        if ok:
            return self._success("restart-node", data, steps)
        return self._error(
            "restart-node",
            "Timeout",
            "Restart did not complete in time.",
            steps,
            data,
            status="timeout",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Volcano Engine ESCloud goal-based control plane CLI"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Include context data in error payloads"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser(
        "provision-info",
        help="Collect necessary info for provisioning (VPCs, subnets, specs, zones)",
    )
    p.set_defaults(goal="provision-info")

    p = subparsers.add_parser("list", help="List ESCloud instances")
    p.add_argument("--page-number", type=int, default=1)
    p.add_argument("--page-size", type=int, default=10)
    p.set_defaults(goal="list")

    p = subparsers.add_parser(
        "provision", help="Create an ESCloud instance and wait until Running"
    )
    p.add_argument("--name", required=True, help="Instance name")
    p.add_argument("--vpc-id", required=True, help="VPC ID")
    p.add_argument("--subnet-id", required=True, help="Subnet ID")
    p.add_argument("--admin-password", required=True, help="Admin password")
    p.add_argument("--version", required=True, help="ESCloud version (e.g. V7_10)")
    p.add_argument(
        "--charge-type", default="PostPaid", help="Charge type (PostPaid or PrePaid)"
    )

    p.add_argument("--master-spec", default="", help="Master node resource spec name")
    p.add_argument("--master-count", type=int, default=3, help="Master node count")
    p.add_argument(
        "--master-storage-spec", default="", help="Master node storage spec name"
    )
    p.add_argument(
        "--master-storage-size",
        type=int,
        default=None,
        help="Master node storage size in GiB",
    )

    p.add_argument("--hot-spec", required=True, help="Hot node resource spec name")
    p.add_argument("--hot-count", type=int, default=2, help="Hot node count")
    p.add_argument(
        "--hot-storage-spec", required=True, help="Hot node storage spec name"
    )
    p.add_argument(
        "--hot-storage-size",
        type=int,
        required=True,
        help="Hot node storage size in GiB",
    )

    p.add_argument("--kibana-spec", default="", help="Kibana node resource spec name")
    p.add_argument("--kibana-count", type=int, default=1, help="Kibana node count")

    p.add_argument(
        "--poll-interval", type=int, default=5, help="Polling interval in seconds"
    )
    p.add_argument(
        "--timeout", type=int, default=600, help="Polling timeout in seconds"
    )
    p.set_defaults(goal="provision")

    p = subparsers.add_parser(
        "deprovision", help="Delete an ESCloud instance and wait until destroyed"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument(
        "--confirm", required=True, help="Must exactly match the instance ID to confirm"
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Force deletion by disabling deletion protection if enabled",
    )
    p.add_argument(
        "--poll-interval", type=int, default=5, help="Polling interval in seconds"
    )
    p.add_argument(
        "--timeout", type=int, default=600, help="Polling timeout in seconds"
    )
    p.set_defaults(goal="deprovision")

    p = subparsers.add_parser(
        "detail", help="Fetch status and raw details for an ESCloud instance"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.set_defaults(goal="detail")

    p = subparsers.add_parser(
        "scale", help="Scale ESCloud node spec or count and wait until Running"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument(
        "--node-type", required=True, help="Node type (Master, Hot, Kibana, etc.)"
    )
    p.add_argument("--spec-name", required=True, help="Target resource spec name")
    p.add_argument("--count", type=int, required=True, help="Target node count")
    p.add_argument(
        "--storage-spec-name", default="", help="Optional target storage spec name"
    )
    p.add_argument(
        "--storage-size",
        type=int,
        default=None,
        help="Optional target storage size in GiB",
    )
    p.add_argument(
        "--poll-interval", type=int, default=5, help="Polling interval in seconds"
    )
    p.add_argument(
        "--timeout", type=int, default=600, help="Polling timeout in seconds"
    )
    p.set_defaults(goal="scale")

    p = subparsers.add_parser(
        "public-access", help="Toggle public access for ESCloud endpoint"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--enable", type=str_to_bool, required=True, help="true/false")
    add_eip_alloc_args(p)
    p.add_argument(
        "--poll-interval", type=int, default=5, help="Polling interval in seconds"
    )
    p.add_argument(
        "--timeout", type=int, default=600, help="Polling timeout in seconds"
    )
    p.set_defaults(goal="public-access")

    p = subparsers.add_parser(
        "allowlist", help="Set IP allowlist and wait until Running"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--group-name", default="default", help="Group name")
    p.add_argument("--ips", required=True, help="Comma-separated CIDRs/IPs")
    p.add_argument(
        "--type",
        default="PRIVATE_ES",
        help="Allowlist type (e.g. PRIVATE_ES, PUBLIC_ES)",
    )
    p.add_argument(
        "--poll-interval", type=int, default=5, help="Polling interval in seconds"
    )
    p.add_argument(
        "--timeout", type=int, default=600, help="Polling timeout in seconds"
    )
    p.set_defaults(goal="allowlist")

    p = subparsers.add_parser(
        "reset-password", help="Reset admin password and wait until Running"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--admin-password", required=True, help="New admin password")
    p.add_argument(
        "--poll-interval", type=int, default=5, help="Polling interval in seconds"
    )
    p.add_argument(
        "--timeout", type=int, default=600, help="Polling timeout in seconds"
    )
    p.set_defaults(goal="reset-password")

    p = subparsers.add_parser("maintenance", help="Configure maintenance window")
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument(
        "--day", required=True, help="Maintenance days (comma-separated, e.g. Mon,Tue)"
    )
    p.add_argument(
        "--time", required=True, help="Maintenance time window (e.g. 02:00-06:00)"
    )
    p.set_defaults(goal="maintenance")

    p = subparsers.add_parser("rename", help="Rename instance display name")
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--name", required=True, help="New instance name")
    p.set_defaults(goal="rename")

    p = subparsers.add_parser(
        "restart-node", help="Restart a specific node and wait until Running"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--node-id", required=True, help="Node name to restart")
    p.add_argument("--force", action="store_true", help="Force restart")
    p.add_argument(
        "--poll-interval", type=int, default=5, help="Polling interval in seconds"
    )
    p.add_argument(
        "--timeout", type=int, default=600, help="Polling timeout in seconds"
    )
    p.set_defaults(goal="restart-node")

    return parser


def dispatch(control_plane: ControlPlane, args: argparse.Namespace) -> dict[str, Any]:
    goal = args.goal
    if goal == "provision-info":
        return control_plane.provision_info(args)
    elif goal == "list":
        return control_plane.list(args)
    elif goal == "provision":
        return control_plane.provision(args)
    elif goal == "deprovision":
        return control_plane.deprovision(args)
    elif goal == "detail":
        return control_plane.detail(args)
    elif goal == "scale":
        return control_plane.scale(args)
    elif goal == "public-access":
        return control_plane.public_access(args)
    elif goal == "allowlist":
        return control_plane.allowlist(args)
    elif goal == "reset-password":
        return control_plane.reset_password(args)
    elif goal == "maintenance":
        return control_plane.maintenance(args)
    elif goal == "rename":
        return control_plane.rename(args)
    elif goal == "restart-node":
        return control_plane.restart_node(args)
    raise WorkflowError("Invalid Command", f"Unsupported goal {args.goal!r}.")


def main() -> None:
    try:
        parser = build_parser()
        args = parser.parse_args()

        control_plane = ControlPlane(debug=args.debug)

        resp = dispatch(control_plane, args)
        emit(resp)
    except WorkflowError as exc:
        error_label = exc.error
        details_label = exc.details or str(exc)
        if error_label in ("API Error", "Unexpected Error") and details_label:
            error_label = details_label
            details_label = ""

        payload = {
            "status": "error",
            "goal": getattr(args, "goal", ""),
            "error": error_label,
        }
        if details_label:
            payload["details"] = details_label

        payload["data"] = exc.data
        payload["steps_completed"] = exc.steps_completed
        emit(payload, exit_code=1)
    except Exception as exc:
        import traceback

        print(
            f"FATAL: Unhandled exception: {type(exc).__name__}: {exc}", file=sys.stderr
        )
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
