"""
配置加载器

单例模式，全局只加载一次配置，避免重复 IO。
所有模块通过 `from doramate_agent.utils.config import get_config` 获取配置。
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def find_project_root() -> Path:
    """
    自动定位项目根目录。

    查找逻辑：从当前文件开始向上找，直到找到含 `config/project.yaml` 的目录。
    这样无论用户从哪里调用，路径都能正确解析。
    """
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "config" / "project.yaml").exists():
            return parent
    raise FileNotFoundError(
        "无法定位项目根目录。请确认 config/project.yaml 文件存在。"
    )


PROJECT_ROOT = find_project_root()


class Config:
    """配置访问器。支持点路径访问，如 config.get('project.name')。"""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def get(self, key_path: str, default: Any = None) -> Any:
        """支持点路径：config.get('project.brand.primary_color')"""
        keys = key_path.split(".")
        value = self._data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    @property
    def raw(self) -> dict[str, Any]:
        return self._data


@lru_cache(maxsize=1)
def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_project_config() -> Config:
    """获取项目身份配置（DoraMate 是什么、谁的项目）"""
    return Config(_load_yaml(PROJECT_ROOT / "config" / "project.yaml"))


@lru_cache(maxsize=1)
def get_agent_config() -> Config:
    """获取 Agent 行为配置（用什么 LLM、生成偏好等）"""
    return Config(_load_yaml(PROJECT_ROOT / "config" / "agent.yaml"))


def get_config() -> dict[str, Config]:
    """一次性获取所有配置。"""
    # 加载 .env 文件中的环境变量
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    return {
        "project": get_project_config(),
        "agent": get_agent_config(),
    }


def get_secret(key: str, required: bool = True) -> str | None:
    """
    从环境变量获取密钥。

    永远不要把密钥写在配置文件里，统一从环境变量读取。
    """
    # 确保 .env 已加载
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    value = os.getenv(key)
    if not value and required:
        raise ValueError(
            f"缺少必需的环境变量 {key}。\n"
            f"请检查 {PROJECT_ROOT / '.env'} 文件，参考 .env.example。"
        )
    return value
