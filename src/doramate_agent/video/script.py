"""
视频脚本生成器

输入主题 → 输出结构化的视频脚本：
    - 标题（3 个备选）
    - 分镜列表（含画面描述、口播文本、时长）
    - 封面建议（含图像生成 prompt）

输出可被 image_gen / tts / composite 模块直接消费。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from ..llm import get_llm
from ..utils.prompts import render_prompt
from ..utils import get_project_config, PROJECT_ROOT

logger = logging.getLogger(__name__)


@dataclass
class Scene:
    """单个分镜。"""
    index: int
    duration_seconds: float
    visual_description: str   # 给 AI 生图的描述
    narration: str            # 给 TTS 的口播文本
    on_screen_text: str = ""  # 屏幕大字（可选）


@dataclass
class VideoScript:
    """完整视频脚本。"""
    topic: str
    title_candidates: list[str]
    selected_title: str
    description: str
    scenes: list[Scene]
    thumbnail_prompts: list[str]   # 3 个封面图的生成 prompt
    total_duration: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "title_candidates": self.title_candidates,
            "selected_title": self.selected_title,
            "description": self.description,
            "scenes": [asdict(s) for s in self.scenes],
            "thumbnail_prompts": self.thumbnail_prompts,
            "total_duration": self.total_duration,
        }


# 视频脚本生成的 system prompt
SCRIPT_GENERATION_PROMPT = """你是一个开源技术视频的脚本编剧，正在为 {project_name} 项目制作 3 分钟的科普视频。

【项目背景】
{project_description}
GitHub: {project_github}

【知识库】（必须严格遵守，不能编造技术细节）
{knowledge_base}

【视频主题】
{topic}

【用户额外提示】
{user_hint}

【任务】
生成一份完整的视频脚本。视频特点：
- 总时长 180 秒（3 分钟）
- 8-12 个分镜
- 每个分镜配画面描述（用于 AI 生图）和口播文本（用于 TTS）
- 风格：友好、有节奏、技术感
- 黄金 10 秒原则：开头必须强钩子

【输出严格 JSON 格式】（不要有任何前后多余文字，不要 markdown 代码块标记）
{{
  "title_candidates": [
    "标题1（≤30字，带钩子）",
    "标题2",
    "标题3"
  ],
  "selected_title": "推荐使用的标题",
  "description": "视频简介（150 字左右，发布到 B 站/小红书时用）",
  "scenes": [
    {{
      "index": 1,
      "duration_seconds": 8,
      "visual_description": "（详细描述这一画面：构图、风格、色彩、内容元素，会用于AI生图）",
      "narration": "（这一镜头要说的话，要口语化，不要书面语）",
      "on_screen_text": "（屏幕上要显示的大字，可空字符串）"
    }},
    ...
  ],
  "thumbnail_prompts": [
    "封面图1的AI生成prompt（英文，详细，包含构图/色彩/字体/主体）",
    "封面图2的AI生成prompt",
    "封面图3的AI生成prompt"
  ]
}}

【关键约束】
- 所有 scenes 的 duration_seconds 加起来应该 ≈ 180 秒
- visual_description 要详细到能让 AI 直接生图（描述具体物体、构图、风格、色彩）
- visual_description 只描述该分镜的主体内容与构图，不要自行切换画风；统一画风由后续 STYLE LOCK 控制
- 不要要求生成 DoraMate 真实产品截图、真实机器人硬件 demo 或已上线 UI；只能生成概念图、学习路线图、数据流示意、官网/开源社区氛围图
- narration 要口语化，每段 15-30 字符为宜，避免长难句
- 必须是合法可解析的 JSON（用双引号，不要尾随逗号）
- 视频结尾要有 CTA（关注/点赞/GitHub搜项目名）

直接输出 JSON，不要任何解释、标记或前置说明。"""


class ScriptGenerator:
    """视频脚本生成器。"""

    def __init__(self):
        self.llm = get_llm(task="content_generation")

    def _load_knowledge_base(self) -> str:
        cfg = get_project_config()
        kb_path = cfg.get("knowledge_base.path", "data/dora_knowledge.md")
        full_path = PROJECT_ROOT / kb_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return ""

    def generate(
        self,
        topic: str,
        user_hint: str = "",
        target_duration: int = 180,
    ) -> VideoScript:
        """生成视频脚本。"""
        prompt = render_prompt(
            template=SCRIPT_GENERATION_PROMPT,
            topic=topic,
            knowledge_base=self._load_knowledge_base(),
            user_hint=user_hint,
        )

        response = self.llm.generate(prompt=prompt, temperature=0.8, max_tokens=4000)
        logger.info(f"脚本生成完成（成本 ¥{response.cost_cny}）")

        # 解析 JSON
        json_str = self._extract_json(response.content)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败：{e}\n返回内容：{response.content[:500]}")
            raise

        # 构造 VideoScript
        scenes = [Scene(**s) for s in data.get("scenes", [])]
        script = VideoScript(
            topic=topic,
            title_candidates=data.get("title_candidates", []),
            selected_title=data.get("selected_title", ""),
            description=data.get("description", ""),
            scenes=scenes,
            thumbnail_prompts=data.get("thumbnail_prompts", []),
            total_duration=sum(s.duration_seconds for s in scenes),
        )
        return script

    def _extract_json(self, text: str) -> str:
        """从模型回复中提取 JSON（容错：去除可能的 markdown 包裹）。"""
        # 移除 ```json ... ``` 包裹
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text)
        # 找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"无法在响应中找到 JSON：{text[:200]}")
        return text[start : end + 1]
