"""DeepSeek LLM Provider"""
from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI

from .base import BaseLLM, LLMRegistry, LLMResponse
from ..utils import get_secret

logger = logging.getLogger(__name__)


@LLMRegistry.register("deepseek")
class DeepSeekLLM(BaseLLM):
    """DeepSeek API client。
    
    DeepSeek 兼容 OpenAI SDK，所以直接复用 openai 库。
    定价（2026 年初）：deepseek-chat 输入 ¥0.001/千tokens，输出 ¥0.002/千tokens
    """

    DEFAULT_MODEL = "deepseek-chat"
    BASE_URL = "https://api.deepseek.com/v1"
    
    # 定价（每百万 tokens，人民币）
    PRICE_INPUT = 1.0    # ¥/M tokens
    PRICE_OUTPUT = 2.0   # ¥/M tokens

    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or self.DEFAULT_MODEL
        api_key = api_key or get_secret("DEEPSEEK_API_KEY")
        self.client = OpenAI(api_key=api_key, base_url=self.BASE_URL)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = response.usage
        cost = (
            usage.prompt_tokens * self.PRICE_INPUT / 1_000_000
            + usage.completion_tokens * self.PRICE_OUTPUT / 1_000_000
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            provider="deepseek",
            tokens_in=usage.prompt_tokens,
            tokens_out=usage.completion_tokens,
            cost_cny=round(cost, 4),
        )
