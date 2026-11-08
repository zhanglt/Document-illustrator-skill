"""为所有 Agent 提供统一的技能配置入口。"""

from pathlib import Path

from dotenv import load_dotenv


def find_and_load_env():
    """只加载 ~/.agents/skills/document-illustrator/.env，保留文件值优先规则。"""
    env_path = Path.home() / ".agents" / "skills" / "document-illustrator" / ".env"
    if not env_path.is_file():
        return False
    load_dotenv(env_path, override=True, encoding="utf-8")
    return True
