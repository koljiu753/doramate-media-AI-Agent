"""
Prompt 模板上下文构建器

把 project.yaml 里的项目身份变量注入到 prompt 模板中。

为什么要这样做：
- 让 prompt 模板里写 {project_name} 而不是硬编码 "DoraMate"
- 让别人 fork 后只改 project.yaml 就能用
- 让团队不同成员可以用不同的 voice_style
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..utils import get_project_config, PROJECT_ROOT


def build_template_context(
    contributor_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    构建 prompt 模板的变量上下文。
    
    Args:
        contributor_id: 内容作者 ID（从 project.yaml.team.contributors 取）
                       未指定则用第一个 contributor
    
    Returns:
        可直接用 .format(**ctx) 的变量字典
    """
    cfg = get_project_config()
    project = cfg.get("project", {})
    team = cfg.get("team", {})
    sponsors = cfg.get("sponsors.required_attribution", [])

    contributors = team.get("contributors", [])
    if not contributors:
        author = {"name": "项目组", "voice_style": ""}
    elif contributor_id:
        author = next(
            (c for c in contributors if c.get("id") == contributor_id),
            contributors[0],
        )
    else:
        author = contributors[0]

    sponsor_line = ""
    if sponsors:
        s = sponsors[0]
        sponsor_line = s.get("combined", f"{s.get('text_zh', '')}｜{s.get('text_en', '')}")

    # 标准结尾模板
    standard_footer = build_standard_footer(project, sponsor_line)

    return {
        # 项目基础信息
        "project_name": project.get("name", "项目"),
        "project_display_name": project.get("display_name", project.get("name", "")),
        "project_tagline": project.get("tagline", ""),
        "project_description": project.get("description", "").strip(),
        "project_github": project.get("github", ""),
        "project_website": project.get("website", ""),
        "project_docs": project.get("docs", ""),
        "project_keywords": ", ".join(project.get("keywords", [])),
        # 上游项目（如有）
        "parent_project_name": project.get("parent_project", {}).get("name", ""),
        "parent_project_url": project.get("parent_project", {}).get("url", ""),
        "parent_project_website": project.get("parent_project", {}).get("website", ""),
        # 作者
        "author_name": author.get("name", ""),
        "author_role": author.get("role", ""),
        "author_voice_style": author.get("voice_style", ""),
        # 赞助/必标
        "sponsor_attribution": sponsor_line,
        # 拼好的标准结尾
        "standard_footer": standard_footer,
    }


def build_standard_footer(project: dict, sponsor_line: str) -> str:
    """构造内容标准结尾（项目链接 + 必标）"""
    lines = ["---", "", "🔗 **项目链接**"]
    if project.get("github"):
        lines.append(f"- GitHub: {project['github']}")
    if project.get("website"):
        lines.append(f"- 官网: {project['website']}")
    if project.get("parent_project", {}).get("website"):
        lines.append(f"- 上游项目: {project['parent_project']['website']}")
    if sponsor_line:
        lines.append("")
        lines.append(f"> {sponsor_line}")
    return "\n".join(lines)


def render_prompt(
    template: str,
    topic: str,
    knowledge_base: str = "",
    user_hint: str = "",
    contributor_id: Optional[str] = None,
    extra: Optional[dict] = None,
) -> str:
    """
    渲染 prompt 模板。
    
    Args:
        template: 含 {var} 占位符的模板字符串
        topic: 内容主题
        knowledge_base: 知识库内容（防止 AI 胡说）
        user_hint: 用户额外提示
        contributor_id: 作者 ID
        extra: 额外变量
    """
    ctx = build_template_context(contributor_id=contributor_id)
    ctx.update({
        "topic": topic,
        "knowledge_base": knowledge_base or "（无）",
        "user_hint": user_hint or "（无）",
    })
    if extra:
        ctx.update(extra)

    # 用容错性高的方式渲染：未知变量保留原样，不报错
    class SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    
    try:
        # 先尝试 Python str.format（更严格但快）
        return template.format(**ctx)
    except (KeyError, IndexError):
        # 容错模式
        from string import Formatter
        return Formatter().vformat(template, (), SafeDict(**ctx))
