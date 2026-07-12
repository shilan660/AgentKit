import os
from pathlib import Path
from dotenv import load_dotenv
from agentkit.toolkit import sdk
from agentkit.toolkit.sdk import AgentConfig

load_dotenv(Path("secret/.env"))

# 你的第一个 Agent 项目目录
project_root = Path("first_agent")

# 1. 初始化项目
if not project_root.exists():
    sdk.init_project(
        project_name=project_root.name,
        template="basic",
        project_root=str(project_root),
    )
    print(f"示例项目已创建在: {project_root.resolve()}")
else:
    print(f"示例项目已存在: {project_root.resolve()}")

# 2. 加载 agentkit.yaml
config = AgentConfig.load(project_root)

# 3. 写入 Agent 运行时环境变量
config.add_runtime_env("MODEL_AGENT_NAME", os.getenv("MODEL_AGENT_NAME"))
config.add_runtime_env("MODEL_AGENT_API_KEY", os.getenv("MODEL_AGENT_API_KEY"))

# 4. 保存配置
config.save()

print("已成功向 agentkit.yaml 中写入运行时环境变量:")
print(config.runtime_envs)
