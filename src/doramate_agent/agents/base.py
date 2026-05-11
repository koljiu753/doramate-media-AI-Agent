"""
Agent 基类

所有 Agent（创作/选题/视频/周报）都继承这个，统一行为模式。
"""
from __future__ import annotations

import abc
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils import get_agent_config, get_project_config, PROJECT_ROOT

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    """所有 Agent 的基类。"""

    agent_name: str = "base"

    def __init__(self):
        self.project_config = get_project_config()
        self.agent_config = get_agent_config()
        self._setup_output_dir()

    def _setup_output_dir(self):
        """确保输出目录存在。"""
        output_dir = self.get_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

    def get_output_dir(self) -> Path:
        """获取这个 Agent 的输出目录。"""
        rel_path = self.agent_config.get(
            f"{self.agent_name}.output_dir",
            f"output/{self.agent_name}"
        )
        return PROJECT_ROOT / rel_path

    @abc.abstractmethod
    def run(self, **kwargs) -> Any:
        """子类必须实现：Agent 的主要工作逻辑。"""
        raise NotImplementedError

    def log_event(self, event: str, **details):
        """统一日志格式，便于后续做使用统计。"""
        logger.info(f"[{self.agent_name}] {event} | {details}")
