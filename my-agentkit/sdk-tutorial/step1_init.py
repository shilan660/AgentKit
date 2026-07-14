# 约定一个教程专用的项目路径（project_root 为项目根目录）
from pathlib import Path
from agentkit.toolkit import sdk
from agentkit.toolkit.models import PreflightMode

# script_dir = Path(__file__).resolve().parent
# project_root = script_dir / "tutorial_projects/t01-hello-agent"
# project_name = project_root.name

# print(f'项目将创建在: {project_root.resolve()}')

# # 调用 SDK 的 init_project 创建示例工程（会在 project_root 下生成配置和代码文件）
# result = sdk.init_project(
#     project_name=project_name,
#     template="basic",
#     project_root=str(project_root),
# )

# print("初始化是否成功:", result.success)
# print("项目路径:", result.project_path)
# print("生成的文件列表:")
# for f in result.created_files:
#     print(" -", f)

# # 使用 init_project 返回的 project_path 作为后续操作的项目根目录
# project_root = Path(result.project_path)


# # 定位到刚刚生成的配置文件
# config_file = project_root / "agentkit.yaml"
# print("使用的配置文件:", config_file)

# 调用 sdk.build 进行构建
# build_result = sdk.build(
#     config_file=str(Path("my-agentkit/sdk-tutorial/tutorial_projects/t01-hello-agent/agentkit.yaml")),
#     preflight_mode=PreflightMode.WARN,
# )

# print("构建是否成功:", build_result.success)
# print("镜像信息 image:", build_result.image)
# print("错误信息 error:", build_result.error)

# # 如需查看部分构建日志，可以打印最后若干行
# if build_result.build_logs:
#     print("构建日志示例 (最后 10 行):")
#     for line in build_result.build_logs[-10:]:
#         print(line)


# 调用 sdk.build 进行构建

tutorial_root = Path(__file__).resolve().parent

config_file = (
    tutorial_root
    / "tutorial_projects"
    / "t01-hello-agent"
    / "agentkit.yaml"
)

# build_result = sdk.build(
#     config_file=str(config_file),
#     preflight_mode=PreflightMode.WARN,
# )

# print("构建是否成功:", build_result.success)
# print("镜像信息 image:", build_result.image)
# print("错误信息 error:", build_result.error)

# # 如需查看部分构建日志，可以打印最后若干行
# if build_result.build_logs:
#     print("构建日志示例 (最后 10 行):")
#     for line in build_result.build_logs[-10:]:
#         print(line)

# 部署 Agent
# deploy_result = sdk.deploy(
#     config_file=str(config_file),
#     preflight_mode=PreflightMode.WARN,
# )

# print("部署是否成功:", deploy_result.success)
# print("服务 endpoint_url:", deploy_result.endpoint_url)
# print("错误信息 error:", deploy_result.error)

# # 调用已部署的 Agent
# from agentkit.utils.logging_config import setup_cli_logging, setup_sdk_logging
# setup_sdk_logging("INFO")
# invoke_result = sdk.invoke(
#     payload={"prompt": "你是谁。"},
#     headers={"user_id": "user-1", "session_id": "session-1"},
#     config_file=str(config_file),
# )

# print("调用是否成功:", invoke_result.success)
# print("响应内容 response:")
# print(invoke_result.response)


# 查询状态
status_result = sdk.status(config_file=str(config_file))
print("状态查询是否成功:", status_result.success)
print("当前状态 status:", status_result.status)
print("endpoint_url:", status_result.endpoint_url)
print(status_result)