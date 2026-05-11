"""OpenAI LLM Provider"""
from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI

from .base import BaseLLM, LLMRegistry, LLMResponse
from ..utils import get_secret

logger = logging.getLogger(__name__)


@LLMRegistry.register("openai")
class OpenAILLM(BaseLLM):
    """OpenAI API client。"""

    DEFAULT_MODEL = "gpt-4o-mini"
    
    # 定价（每百万 tokens，美元；按 7.2 汇率换算）
    PRICE_INPUT = 0.15 * 7.2    # USD/M → CNY/M
    PRICE_OUTPUT = 0.6 * 7.2

    def __init__(self, model: str = None, api_key: str = None, base_url: str = None):
        self.model = model or self.DEFAULT_MODEL
        api_key = api_key or get_secret("OPENAI_API_KEY")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)

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
            provider="openai",
            tokens_in=usage.prompt_tokens,
            tokens_out=usage.completion_tokens,
            cost_cny=round(cost, 4),
        )
