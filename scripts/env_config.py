"""为所有 Agent 提供统一的技能配置入口。"""

import io
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from dotenv.parser import parse_stream


_sections = {}
_configured_provider = None
_provider_sections = {"image2-4k": "image2-4k", "nanobanana": "nanobanana", "gemini": "gemini", "cihebi": "cihebi"}


def find_and_load_env():
    """加载统一配置的全局项，缓存分组，分组值仅在选择对应后端时使用。"""
    global _sections, _configured_provider
    _sections = {}
    _configured_provider = None
    env_path = Path.home() / ".agents" / "skills" / "document-illustrator" / ".env"
    if not env_path.is_file():
        return False
    groups = {None: []}
    section = None
    # 使用 dotenv 的绑定解析器，避免把多行引号值中的 [标题] 误识别为分组。
    for binding in parse_stream(io.StringIO(env_path.read_text(encoding="utf-8"))):
        header = re.fullmatch(r"\s*\[([A-Za-z0-9_-]+)\]\s*(?:#[^\n]*)?", binding.original.string.strip())
        if header:
            section = header.group(1)
            if section not in _provider_sections.values():
                raise ValueError(".env 中存在不支持的分组；请使用 [image2-4k]、[nanobanana]、[gemini] 或 [cihebi]")
            groups.setdefault(section, [])
        elif binding.error:
            raise ValueError(f".env 第 {binding.original.line} 行格式错误")
        else:
            groups[section].append(binding.original.string)
    def parse_values(lines):
        return {key: value for key, value in dotenv_values(
            stream=io.StringIO("".join(lines))
        ).items() if value is not None}

    global_values = parse_values(groups.pop(None))
    _configured_provider = global_values.get("ILLUSTRATOR_IMAGE_PROVIDER")
    os.environ.update(global_values)
    _sections = {name: parse_values(lines) for name, lines in groups.items()}
    return True


def get_configured_provider():
    """只返回共享 .env 顶层指定的后端，不接受进程环境或分组覆盖。"""
    return _configured_provider


def get_provider_config(provider):
    """分组覆盖全局及环境变量；后端选择由共享 .env 顶层锁定。"""
    values = dict(os.environ)
    section = _sections.get(_provider_sections.get(provider), {})
    values.update({key: value for key, value in section.items() if key != "ILLUSTRATOR_IMAGE_PROVIDER"})
    return values


def get_proxy_url():
    """读取共享配置中的全局代理，不从后端分组继承。"""
    proxy = os.environ.get("PROXY", "").strip()
    if not proxy:
        return None
    parsed = urlsplit(proxy)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.path not in ("", "/"):
        raise ValueError("PROXY 必须为 http:// 或 https:// 代理地址")
    try:
        parsed.port
    except ValueError:
        raise ValueError("PROXY 端口无效") from None
    return proxy
