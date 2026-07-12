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
from typing import Any, Dict, List, Optional, Set, Tuple

from api import ApiError, EsCloudApi, VpcApi


def print_result(data: Any) -> None:
    print(json.dumps({"status": "success", "data": data}, ensure_ascii=False))


def print_error(msg: str, details: Optional[str] = None) -> None:
    err: Dict[str, Any] = {"error": msg}
    if details:
        err["details"] = details
    print(json.dumps(err, ensure_ascii=False))
    sys.exit(1)


def api_call(fn):
    try:
        response = fn()
        try:
            result = response.to_dict()
        except AttributeError:
            result = str(response)
        print_result(result)
    except ApiError as e:
        msg = str(e)
        instr = ""
        if "TaskIsRunning" in msg:
            instr = "An operation is already in progress. Wait a few minutes and retry, or check status via 'detail'."
        elif any(
            k in msg
            for k in ["BadRequest", "InvalidParameter", "NotFound", "Unauthorized"]
        ):
            instr = "Verify IDs/specs and permissions. Use 'vpc', 'subnet', and 'node_specs' to fetch valid options."
        details = f"{msg}\n\nInstruction: {instr}" if instr else msg
        print_error("API Error", details)
    except Exception as e:
        print_error(
            "Unexpected Error",
            f"{str(e)}\n\nInstruction: Check network connectivity and credentials.",
        )


def str_to_bool(v: str) -> bool:
    if v.lower() in ("true", "1", "yes", "y"):
        return True
    if v.lower() in ("false", "0", "no", "n"):
        return False
    raise argparse.ArgumentTypeError(f"Boolean value expected, got '{v}'")


def _get_clients() -> Tuple[EsCloudApi, VpcApi, Any, str]:
    import ark_shim

    if ark_shim.check_is_ark_env():
        return ark_shim.get_clients()

    import sdk_shim

    return sdk_shim.get_clients()


def get_zone_id_by_subnet(vpc_api: VpcApi, subnet_id: str) -> str:
    resp = vpc_api.describe_subnets({"SubnetIds": [subnet_id]})
    resp_dict = (
        resp.to_dict()
        if hasattr(resp, "to_dict")
        else (resp if isinstance(resp, dict) else {})
    )
    result = resp_dict.get("Result") or resp_dict.get("result") or resp_dict
    subnets = result.get("Subnets") or result.get("subnets") or []
    if not subnets:
        print_error(
            "Subnet Not Found",
            f"Subnet ID '{subnet_id}' does not exist or is not in the current region. Instruction: Run 'vpc' and 'subnet --vpc-id <ID>' to list valid options.",
        )
    first = subnets[0] if isinstance(subnets, list) and subnets else {}
    zone_id = first.get("ZoneId") or first.get("zone_id") or ""
    if not zone_id:
        print_error(
            "Zone Not Found",
            "Failed to derive zone_id from the subnet. Try a different subnet.",
        )
    return zone_id


def _resolve_eip_billing_type(val):
    """
    EIP billing type constants.
    """
    EIP_BILL_TYPES = {
        "PostPaidByBandwidth": 1,
        "PostPaidByTraffic": 2,
        "PrePaid": 3,
    }
    return EIP_BILL_TYPES.get(val, val)


def cmd_list(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {"PageNumber": args.page_number, "PageSize": args.page_size}
    api_call(lambda: es_api.describe_instances(body))


def cmd_detail(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {"InstanceId": args.id}
    api_call(lambda: es_api.describe_instance(body))


def cmd_zones(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {}
    api_call(lambda: es_api.describe_zones(body))


def cmd_node_specs(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    body = {}
    api_call(lambda: es_api.describe_node_available_specs(body))


def cmd_vpc(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {}
    api_call(lambda: vpc_api.describe_vpcs(body))


def cmd_subnet(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {"VpcId": args.vpc_id}
    api_call(lambda: vpc_api.describe_subnets(body))


def cmd_eip_list(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {}
    if args.status:
        body["Status"] = args.status
    api_call(lambda: vpc_api.describe_eip_addresses(body))


def cmd_eip_allocate(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    billing_type = (
        _resolve_eip_billing_type(args.billing_type) or 2
    )  # Default to PostPaidByTraffic
    body = {
        "Bandwidth": args.bandwidth,
        "BillingType": billing_type,
        "Name": args.name,
        "Description": args.description,
        "ISP": args.isp,
    }
    api_call(lambda: vpc_api.allocate_eip_address(body))


def cmd_eip_release(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    body = {"AllocationId": args.allocation_id}
    api_call(lambda: vpc_api.release_eip_address(body))


def cmd_create(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    zone_id = get_zone_id_by_subnet(vpc_api, args.subnet_id)

    node_specs = []
    if args.master_spec:
        node_specs.append(
            {
                "Type": "Master",
                "Number": args.master_count,
                "ResourceSpecName": args.master_spec,
                "StorageSpecName": args.master_storage_spec or args.hot_storage_spec,
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
    if args.kibana_spec:
        node_specs.append(
            {
                "Type": "Kibana",
                "Number": args.kibana_count,
                "ResourceSpecName": args.kibana_spec,
            }
        )

    instance_conf = {
        "InstanceName": args.name,
        "Version": args.version,
        "AdminPassword": args.admin_password,
        "ChargeType": args.charge_type,
        "DeletionProtection": args.deletion_protection,
        "EnableHttps": args.https,
        "EnablePureMaster": args.pure_master
        if args.pure_master is not None
        else (True if args.master_spec else False),
        "ProjectName": "default",
        "RegionId": region,
        "ZoneId": zone_id,
        "VPC": {"VpcId": args.vpc_id},
        "Subnet": {"SubnetId": args.subnet_id},
        "NodeSpecsAssigns": node_specs,
    }

    body = {"InstanceConfiguration": instance_conf}
    api_call(lambda: es_api.create_instance_in_one_step(body))


def cmd_scale(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    assign_kwargs = {
        "Type": args.node_type,
        "Number": args.count,
        "ResourceSpecName": args.spec_name,
    }
    if args.storage_spec_name:
        assign_kwargs["StorageSpecName"] = args.storage_spec_name
    if args.storage_size is not None:
        assign_kwargs["StorageSize"] = args.storage_size

    assign = dict(assign_kwargs)

    body = {
        "InstanceId": args.id,
        "NodeSpecsAssigns": [assign],
    }
    api_call(lambda: es_api.modify_node_spec_in_one_step(body))


def cmd_delete(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    if not getattr(args, "confirm", False):
        print_error(
            "Confirmation Required",
            "Refusing to delete without --confirm. Ask the user to explicitly confirm, then rerun with: control_tools.py delete --id <instance-id> --confirm",
        )
    body = {"InstanceId": args.id}
    api_call(lambda: es_api.release_instance(body))


def cmd_ip_allowlist_get(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    body = {"InstanceId": args.id}
    api_call(lambda: es_api.describe_ip_allow_list(body))


def parse_json_array(raw: str, name: str) -> list:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print_error("Invalid JSON", f"Invalid JSON in {name}: {str(e)}")
    if not isinstance(data, list):
        print_error(
            "Invalid JSON", f"{name} must be a JSON array, e.g. '[\"1.2.3.4/32\"]'"
        )
    return data


def extract_supported_versions_from_node_specs(
    node_specs_dict: Dict[str, Any],
) -> List[str]:
    versions: Set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and k.lower() in (
                    "version",
                    "versionid",
                    "version_id",
                ):
                    versions.add(v)
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(node_specs_dict)

    def sort_key(s: str) -> Tuple[int, str]:
        # Best-effort sorting: prefer known prefixes, then lexical.
        if s.startswith("V"):
            return (0, s)
        if s.startswith("OPEN_SEARCH_"):
            return (1, s)
        return (2, s)

    return sorted(versions, key=sort_key)


def cmd_versions(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    # ESCloud does not expose a dedicated "describe_versions" API in this SDK.
    # Derive versions from DescribeNodeAvailableSpecs output (best-effort), so results stay current.
    body = {}

    def call():
        return es_api.describe_node_available_specs(body)

    try:
        resp = call()
        resp_dict = resp.to_dict() if hasattr(resp, "to_dict") else {}
        versions = extract_supported_versions_from_node_specs(resp_dict)
        if not versions:
            print_result(
                {
                    "versions": [],
                    "note": "No versions found in DescribeNodeAvailableSpecs response. Use 'node_specs' to inspect raw output or consult the console.",
                }
            )
            return
        print_result({"versions": versions})
    except ApiError as e:
        print_error("API Error", str(e))
    except Exception as e:
        print_error("Unexpected Error", str(e))


def cmd_ip_allowlist_set(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    ips = parse_json_array(args.ips, "--ips")
    allowlist_type = (args.type or "PRIVATE_ES").strip().upper()
    group = {
        "Name": args.group_name,
        "AllowList": ",".join(ips),
    }
    allowlist = {
        "Groups": [group],
        "Type": allowlist_type,
        "AllowList": "",
    }
    body = {
        "InstanceId": args.id,
        "EsIpAllowList": allowlist,
    }
    api_call(lambda: es_api.modify_ip_allow_list_v2(body))


def cmd_public_network_set(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    body = {
        "InstanceId": args.id,
    }
    if args.enable:
        if not args.eip_id:
            print_error(
                "Missing Parameters", "--eip-id is required when enabling public access"
            )
        body["EsEip"] = {"IsOpen": True, "EipId": args.eip_id}
        api_call(lambda: es_api.create_public_address(body))
    else:
        body["EsEip"] = {"IsOpen": False}
        api_call(lambda: es_api.release_public_address(body))


def cmd_reset_password(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    body = {
        "InstanceId": args.id,
        "NewPassword": args.admin_password,
    }
    api_call(lambda: es_api.reset_admin_password(body))


def cmd_nodes(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {"InstanceId": args.id}
    api_call(lambda: es_api.describe_instance_nodes(body))


def cmd_plugins(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {"InstanceId": args.id}
    api_call(lambda: es_api.describe_instance_plugins(body))


def cmd_rename(args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str):
    body = {"InstanceId": args.id, "NewName": args.name}
    api_call(lambda: es_api.rename_instance(body))


def cmd_maintenance_set(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    # Keep a stable CLI surface even if upstream docs vary:
    # allow either JSON object {"MaintenanceDay":[...],"MaintenanceTime":"..."} or
    # explicit flags --day/--time.
    maintenance_day = args.day
    maintenance_time = args.time
    if args.setting:
        setting = json.loads(args.setting)
        if not isinstance(setting, dict):
            print_error("Invalid --setting", "--setting must be a JSON object")
        if "MaintenanceDay" in setting and not maintenance_day:
            maintenance_day = setting.get("MaintenanceDay")
        if "MaintenanceTime" in setting and not maintenance_time:
            maintenance_time = setting.get("MaintenanceTime")
        if "maintenance_day" in setting and not maintenance_day:
            maintenance_day = setting.get("maintenance_day")
        if "maintenance_time" in setting and not maintenance_time:
            maintenance_time = setting.get("maintenance_time")
    if not maintenance_time:
        print_error(
            "Missing Parameters",
            "Provide --time or --setting containing MaintenanceTime.",
        )
    if isinstance(maintenance_day, str) and maintenance_day:
        # Accept common user inputs (Mon/Tue, Monday/Tuesday, MONDAY/TUESDAY) and normalize to
        # full uppercase day names required by the API.
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
        maintenance_day = [day_map.get(d, d) for d in raw_days]

    body = {
        "InstanceId": args.id,
        "MaintenanceDay": maintenance_day,
        "MaintenanceTime": maintenance_time,
    }
    api_call(lambda: es_api.modify_maintenance_setting(body))


def cmd_deletion_protection_set(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    body = {
        "InstanceId": args.id,
        "DeletionProtection": args.enabled,
    }
    api_call(lambda: es_api.modify_deletion_protection(body))


def cmd_restart_node(
    args, es_api: EsCloudApi, vpc_api: VpcApi, configuration, region: str
):
    body = {
        "InstanceId": args.id,
        "NodeName": args.node_id,
        "Force": args.force,
    }
    api_call(lambda: es_api.restart_node(body))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Volcano Engine ESCloud control tools CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("list", help="List ESCloud instances")
    p.add_argument("--page-number", type=int, default=1)
    p.add_argument("--page-size", type=int, default=10)
    p.set_defaults(func=cmd_list)

    p = subparsers.add_parser("detail", help="Get instance details")
    p.add_argument("--id", required=True, help="Instance ID")
    p.set_defaults(func=cmd_detail)

    p = subparsers.add_parser("create", help="Create a new instance (one step)")
    p.add_argument("--name", required=True, help="Instance name")
    p.add_argument(
        "--version",
        required=True,
        help="Version (e.g. V7_10, V8_18, OPEN_SEARCH_2_9, OPEN_SEARCH_3_3)",
    )
    p.add_argument("--vpc-id", required=True, help="VPC ID")
    p.add_argument("--subnet-id", required=True, help="Subnet ID (used to derive zone)")
    p.add_argument("--admin-password", required=True, help="Admin password")
    p.add_argument(
        "--charge-type",
        default="PostPaid",
        help="Charge type (PostPaid or PrePaid). Default: PostPaid",
    )
    p.add_argument(
        "--https", type=str_to_bool, default=True, help="Enable HTTPS (default: true)"
    )
    p.add_argument(
        "--deletion-protection",
        type=str_to_bool,
        default=True,
        help="Deletion protection (default: true)",
    )

    p.add_argument(
        "--master-spec",
        default="",
        help="Optional master node resource spec name. If provided, pure master nodes are enabled.",
    )
    p.add_argument(
        "--master-count", type=int, default=3, help="Master node count (default: 3)"
    )
    p.add_argument(
        "--master-storage-spec",
        default="",
        help="Optional master node storage spec name.",
    )
    p.add_argument(
        "--master-storage-size",
        type=int,
        default=None,
        help="Optional master node storage size in GiB.",
    )
    p.add_argument(
        "--pure-master",
        type=str_to_bool,
        default=None,
        help="Explicitly enable/disable pure master nodes.",
    )

    p.add_argument("--hot-spec", required=True, help="Hot node resource spec name")
    p.add_argument(
        "--hot-count", type=int, default=2, help="Hot node count (default: 2)"
    )
    p.add_argument(
        "--hot-storage-spec", required=True, help="Hot node storage spec name"
    )
    p.add_argument(
        "--hot-storage-size",
        type=int,
        required=True,
        help="Hot node storage size in GiB",
    )

    p.add_argument(
        "--kibana-spec", default="", help="Optional Kibana node resource spec name"
    )
    p.add_argument(
        "--kibana-count", type=int, default=1, help="Kibana node count (default: 1)"
    )
    p.set_defaults(func=cmd_create)

    p = subparsers.add_parser("scale", help="Scale node spec/count (one step)")
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument(
        "--node-type",
        required=True,
        help="Node type (Master, Hot, Warm, Cold, Coordinator, Kibana, Other)",
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
    p.set_defaults(func=cmd_scale)

    p = subparsers.add_parser("delete", help="Delete an instance")
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument(
        "--confirm", action="store_true", help="Required safety flag for deletion"
    )
    p.set_defaults(func=cmd_delete)

    p = subparsers.add_parser("vpc", help="List VPCs")
    p.set_defaults(func=cmd_vpc)

    p = subparsers.add_parser("subnet", help="List subnets in a VPC")
    p.add_argument("--vpc-id", required=True, help="VPC ID")
    p.set_defaults(func=cmd_subnet)

    p = subparsers.add_parser("zones", help="List available zones")
    p.set_defaults(func=cmd_zones)

    p = subparsers.add_parser("node_specs", help="List node available specs")
    p.set_defaults(func=cmd_node_specs)

    p = subparsers.add_parser(
        "versions",
        help="Best-effort list of supported versions (derived from node_specs)",
    )
    p.set_defaults(func=cmd_versions)

    p = subparsers.add_parser("ip_allowlist_get", help="Get IP allowlist")
    p.add_argument("--id", required=True, help="Instance ID")
    p.set_defaults(func=cmd_ip_allowlist_get)

    p = subparsers.add_parser("ip_allowlist_set", help="Set IP allowlist")
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--group-name", required=True, help="Group name")
    p.add_argument("--ips", required=True, help="JSON array of CIDRs/IPs")
    p.add_argument(
        "--type",
        default="PRIVATE_ES",
        help="Allowlist type (default: PRIVATE_ES). Use PUBLIC_ES when managing a public endpoint allowlist, if supported by your instance.",
    )
    p.set_defaults(func=cmd_ip_allowlist_set)

    p = subparsers.add_parser("reset_password", help="Reset admin password")
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--admin-password", required=True, help="New admin password")
    p.set_defaults(func=cmd_reset_password)

    p = subparsers.add_parser("nodes", help="Describe nodes in an instance")
    p.add_argument("--id", required=True, help="Instance ID")
    p.set_defaults(func=cmd_nodes)

    p = subparsers.add_parser("plugins", help="Describe installed plugins")
    p.add_argument("--id", required=True, help="Instance ID")
    p.set_defaults(func=cmd_plugins)

    p = subparsers.add_parser("rename", help="Rename instance display name")
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--name", required=True, help="New instance name")
    p.set_defaults(func=cmd_rename)

    p = subparsers.add_parser(
        "maintenance_set", help="Set maintenance window/setting (JSON pass-through)"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument(
        "--day", default=None, help="Maintenance days (comma-separated) e.g. Mon,Tue"
    )
    p.add_argument(
        "--time",
        default="",
        help="Maintenance time window (required if --setting omitted)",
    )
    p.add_argument(
        "--setting",
        default="",
        help="Optional JSON object containing MaintenanceDay/MaintenanceTime",
    )
    p.set_defaults(func=cmd_maintenance_set)

    p = subparsers.add_parser(
        "deletion_protection_set", help="Enable/disable deletion protection"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--enabled", type=str_to_bool, required=True, help="true or false")
    p.set_defaults(func=cmd_deletion_protection_set)

    p = subparsers.add_parser("restart_node", help="Restart a specific node")
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument("--node-id", required=True, help="Node name")
    p.add_argument(
        "--force",
        type=str_to_bool,
        default=False,
        help="Force restart (default: false)",
    )
    p.set_defaults(func=cmd_restart_node)

    p = subparsers.add_parser(
        "public_network", help="Enable/disable public network access (EIP)"
    )
    p.add_argument("--id", required=True, help="Instance ID")
    p.add_argument(
        "--enable",
        type=str_to_bool,
        default=True,
        help="Enable or disable public access (default: true)",
    )
    p.add_argument(
        "--eip-id", default="", help="EIP allocation ID (required when enabling)"
    )

    p.set_defaults(func=cmd_public_network_set)

    p = subparsers.add_parser("eip_list", help="List EIP addresses")
    p.add_argument(
        "--status",
        choices=["Available", "Attaching", "Attached", "Detaching", "Releasing"],
        help="Optional filter by status",
    )
    p.set_defaults(func=cmd_eip_list)

    p = subparsers.add_parser("eip_allocate", help="Allocate (create) a new EIP")
    p.add_argument(
        "--bandwidth", type=int, default=1, help="Bandwidth in Mbps (default: 1)"
    )
    p.add_argument(
        "--billing-type",
        default="PostPaidByTraffic",
        help="Billing type (PostPaidByBandwidth, PostPaidByTraffic, PrePaid). Default: PostPaidByTraffic",
    )
    p.add_argument("--name", default="", help="Optional EIP name")
    p.add_argument("--description", default="", help="Optional EIP description")
    p.add_argument("--isp", default="BGP", help="ISP (BGP, etc.). Default: BGP")
    p.set_defaults(func=cmd_eip_allocate)

    p = subparsers.add_parser("eip_release", help="Release (delete) an EIP")
    p.add_argument("--allocation-id", required=True, help="EIP Allocation ID")
    p.set_defaults(func=cmd_eip_release)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    es_api, vpc_api, configuration, region = _get_clients()
    args.func(args, es_api, vpc_api, configuration, region)


if __name__ == "__main__":
    main()
