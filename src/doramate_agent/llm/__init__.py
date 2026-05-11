"""
LLM 工厂入口

使用方式：
    from doramate_agent.llm import get_llm
    
    # 默认（用 agent.yaml 里 default_provider）
    llm = get_llm()
    response = llm.generate("你好")
    print(response.content, response.cost_cny)
    
    # 指定 provider
    llm = get_llm("openai")
    
    # 不同任务用不同 LLM
    llm = get_llm(task="content_generation")
"""
from __future__ import annotations

import logging
from typing import Optional

from .base import BaseLLM, LLMRegistry, LLMResponse
from ..utils import get_agent_config

logger = logging.getLogger(__name__)


# 触发注册（importing 时装饰器会自动注册）
# 容错：某个 Provider 缺依赖不影响其他 Provider 可用
def _safe_import(module_name: str):
    try:
        __import__(f"doramate_agent.llm.{module_name}")
    except ImportError as e:
        logger.debug(f"LLM Provider [{module_name}] 不可用：{e}")


for _m in ["deepseek", "openai_provider"]:
    _safe_import(_m)


def get_llm(provider: Optional[str] = None, task: Optional[str] = None) -> BaseLLM:
    """
    获取 LLM 实例。
    
    优先级：
        1. 显式传 provider
        2. 根据 task 从 task_providers 配置查找
        3. 默认 default_provider
    """
    config = get_agent_config()
    
    if provider is None:
        if task:
            provider = config.get(f"llm.task_providers.{task}")
        if not provider:
            provider = config.get("llm.default_provider", "deepseek")
    
    logger.info(f"创建 LLM Provider: {provider}" + (f" (task={task})" if task else ""))
    return LLMRegistry.create(provider)


def list_providers() -> list[str]:
    """列出所有已注册的 LLM Provider。"""
    return LLMRegistry.list_providers()


__all__ = ["get_llm", "list_providers", "BaseLLM", "LLMResponse"]
