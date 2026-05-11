"""
平台插件系统

平台插件 = plugins/platforms/{id}.yaml + prompts/platforms/{id}.txt

加新平台的步骤（无需改 Python 代码）：
    1. 复制 plugins/platforms/csdn.yaml → 改成 my_platform.yaml
    2. 复制 prompts/platforms/csdn.txt → 改成 my_platform.txt
    3. 调整 yaml 配置（id、name、style 等）
    4. 重新运行 Agent，新平台自动出现
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..utils import PROJECT_ROOT

logger = logging.getLogger(__name__)


@dataclass
class PlatformPlugin:
    """单个平台的插件描述。"""
    id: str
    name: str
    display_name: str
    enabled: bool
    profile: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)
    seo: dict[str, Any] = field(default_factory=dict)
    prompt_template: str = ""
    publishing: dict[str, Any] = field(default_factory=dict)
    required_elements: list[str] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)

    @property
    def prompt_file_path(self) -> Path:
        """完整的 prompt 模板路径。"""
        return PROJECT_ROOT / self.prompt_template

    def load_prompt_template(self) -> str:
        """加载这个平台的 prompt 模板。"""
        path = self.prompt_file_path
        if not path.exists():
            raise FileNotFoundError(
                f"平台 [{self.id}] 的 prompt 模板不存在：{path}\n"
                f"请创建 {self.prompt_template}"
            )
        return path.read_text(encoding="utf-8")


class PlatformRegistry:
    """平台插件注册表（自动扫描 plugins/platforms/ 目录）。"""

    def __init__(self):
        self._plugins: dict[str, PlatformPlugin] = {}
        self._loaded = False

    def _load_all(self):
        """扫描 plugins/platforms/ 目录，加载所有 yaml。"""
        plugins_dir = PROJECT_ROOT / "plugins" / "platforms"
        if not plugins_dir.exists():
            logger.warning(f"平台插件目录不存在：{plugins_dir}")
            return

        count = 0
        for yaml_file in plugins_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                plugin = PlatformPlugin(**data)
                self._plugins[plugin.id] = plugin
                count += 1
            except Exception as e:
                logger.error(f"加载平台插件失败 {yaml_file.name}：{e}")

        logger.info(f"已加载 {count} 个平台插件：{list(self._plugins.keys())}")
        self._loaded = True

    def get(self, platform_id: str) -> PlatformPlugin:
        if not self._loaded:
            self._load_all()
        if platform_id not in self._plugins:
            raise KeyError(
                f"未知平台：{platform_id}。\n"
                f"已注册：{list(self._plugins.keys())}\n"
                f"添加新平台：在 plugins/platforms/ 下创建 {platform_id}.yaml"
            )
        return self._plugins[platform_id]

    def list_enabled(self) -> list[PlatformPlugin]:
        if not self._loaded:
            self._load_all()
        return [p for p in self._plugins.values() if p.enabled]

    def list_all(self) -> list[PlatformPlugin]:
        if not self._loaded:
            self._load_all()
        return list(self._plugins.values())


@lru_cache(maxsize=1)
def get_platform_registry() -> PlatformRegistry:
    """全局单例。"""
    return PlatformRegistry()


def get_platform(platform_id: str) -> PlatformPlugin:
    """便捷函数。"""
    return get_platform_registry().get(platform_id)
