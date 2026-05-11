"""
LLM 抽象层

所有 LLM Provider 实现统一接口。新增 Provider 只需继承 BaseLLM。

Why this matters for open source：
- 别的项目 fork 后想换成自己的 LLM，只改配置，不改代码
- 国内贡献者可以加阿里通义、智谱 GLM 等
- 隐私要求高的可以用 Ollama 跑本地模型
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """统一的 LLM 响应结构。"""
    content: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_cny: float = 0.0   # 估算成本（人民币），便于成本控制


class BaseLLM(abc.ABC):
    """所有 LLM Provider 必须实现这个接口。"""

    provider_name: str = "base"

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> LLMResponse:
        """生成文本。"""
        raise NotImplementedError

    def health_check(self) -> bool:
        """健康检查：是否可用。"""
        try:
            response = self.generate("回复一个字：OK", max_tokens=10)
            return bool(response.content)
        except Exception as e:
            logger.warning(f"{self.provider_name} 健康检查失败：{e}")
            return False


class LLMRegistry:
    """LLM Provider 注册表。"""

    _providers: dict[str, type[BaseLLM]] = {}

    @classmethod
    def register(cls, name: str):
        """装饰器：注册一个 Provider。"""
        def decorator(provider_cls: type[BaseLLM]):
            cls._providers[name] = provider_cls
            provider_cls.provider_name = name
            return provider_cls
        return decorator

    @classmethod
    def create(cls, name: str, **kwargs) -> BaseLLM:
        """根据名字创建 Provider 实例。"""
        if name not in cls._providers:
            available = ", ".join(cls._providers.keys()) or "（无）"
            raise ValueError(
                f"未知的 LLM Provider：{name}。\n"
                f"已注册的 Provider：{available}\n"
                f"如需添加新 Provider，请在 src/doramate_agent/llm/ 下创建模块。"
            )
        return cls._providers[name](**kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._providers.keys())
