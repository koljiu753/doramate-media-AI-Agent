"""
创作 Agent

输入主题，输出多平台内容。
- 平台插件化：从 plugins/platforms/ 自动发现
- 项目身份注入：自动从 project.yaml 读取项目信息
- LLM 可切换：从 agent.yaml 配置 default/per-task
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import BaseAgent
from ..llm import get_llm
from ..platforms import get_platform_registry, PlatformPlugin
from ..utils.prompts import render_prompt
from ..utils import PROJECT_ROOT

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """单平台生成结果。"""
    platform_id: str
    platform_name: str
    content: str
    file_path: Path
    tokens_used: int
    cost_cny: float
    success: bool = True
    error: Optional[str] = None


@dataclass
class CreatorRunResult:
    """整个创作任务的结果。"""
    topic: str
    timestamp: datetime
    results: list[GenerationResult] = field(default_factory=list)
    total_cost_cny: float = 0.0
    total_tokens: int = 0
    
    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)


def slugify(text: str, max_len: int = 30) -> str:
    """生成文件名安全的 slug。"""
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text)
    return text.strip("-")[:max_len]


class CreatorAgent(BaseAgent):
    """创作 Agent。"""

    agent_name = "creator"

    def __init__(self):
        super().__init__()
        self.llm = get_llm(task="content_generation")
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> str:
        """加载知识库（防止 AI 胡说）。"""
        kb_path = self.project_config.get(
            "knowledge_base.path",
            "data/dora_knowledge.md"
        )
        # 兼容老配置：直接给路径
        if not kb_path:
            kb_path = "data/dora_knowledge.md"
        full_path = PROJECT_ROOT / kb_path
        if not full_path.exists():
            logger.warning(f"知识库文件不存在：{full_path}（生成内容可能不准确）")
            return ""
        return full_path.read_text(encoding="utf-8")

    def generate_for_platform(
        self,
        platform: PlatformPlugin,
        topic: str,
        user_hint: str = "",
        contributor_id: Optional[str] = None,
    ) -> GenerationResult:
        """为单个平台生成内容。"""
        topic_slug = slugify(topic)
        
        try:
            # 加载并渲染 prompt
            template = platform.load_prompt_template()
            prompt = render_prompt(
                template=template,
                topic=topic,
                knowledge_base=self.knowledge_base,
                user_hint=user_hint,
                contributor_id=contributor_id,
            )

            # 调用 LLM
            self.log_event("生成开始", platform=platform.id, topic=topic)
            response = self.llm.generate(
                prompt=prompt,
                temperature=self.agent_config.get("llm.temperature", 0.7),
                max_tokens=self.agent_config.get("llm.max_tokens", 4000),
            )

            # 保存结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            ext = platform.output.get("file_extension", "md")
            filename = f"{timestamp}_{topic_slug}_{platform.id}.{ext}"
            file_path = self.get_output_dir() / filename
            file_path.write_text(response.content, encoding="utf-8")

            self.log_event(
                "生成完成",
                platform=platform.id,
                tokens=response.tokens_in + response.tokens_out,
                cost=response.cost_cny,
            )

            return GenerationResult(
                platform_id=platform.id,
                platform_name=platform.name,
                content=response.content,
                file_path=file_path,
                tokens_used=response.tokens_in + response.tokens_out,
                cost_cny=response.cost_cny,
            )
        except Exception as e:
            logger.exception(f"生成失败：{platform.id}")
            return GenerationResult(
                platform_id=platform.id,
                platform_name=platform.name,
                content="",
                file_path=Path(),
                tokens_used=0,
                cost_cny=0.0,
                success=False,
                error=str(e),
            )

    def run(
        self,
        topic: str,
        platforms: Optional[list[str]] = None,
        user_hint: str = "",
        contributor_id: Optional[str] = None,
    ) -> CreatorRunResult:
        """
        主入口：生成多平台内容。
        
        Args:
            topic: 内容主题
            platforms: 平台 ID 列表，None 则用默认（从 agent.yaml）
            user_hint: 给 Agent 的额外提示
            contributor_id: 作者 ID（用于平台风格）
        """
        registry = get_platform_registry()

        # 决定要生成哪些平台
        if platforms:
            target_platforms = [registry.get(pid) for pid in platforms]
        else:
            default_ids = self.agent_config.get(
                "creator.default_platforms",
                ["csdn", "xiaohongshu", "zhihu", "bilibili", "wechat"],
            )
            target_platforms = [registry.get(pid) for pid in default_ids]

        result = CreatorRunResult(topic=topic, timestamp=datetime.now())

        for platform in target_platforms:
            if not platform.enabled:
                logger.info(f"跳过未启用的平台：{platform.id}")
                continue
            gen_result = self.generate_for_platform(
                platform=platform,
                topic=topic,
                user_hint=user_hint,
                contributor_id=contributor_id,
            )
            result.results.append(gen_result)
            result.total_cost_cny += gen_result.cost_cny
            result.total_tokens += gen_result.tokens_used

        return result
