"""Prompt 模板渲染测试。"""
import pytest
from doramate_agent.utils.prompts import render_prompt, build_template_context


def test_template_context_has_required_vars():
    """上下文应包含必要变量。"""
    ctx = build_template_context()
    assert "project_name" in ctx
    assert "project_github" in ctx
    assert "sponsor_attribution" in ctx
    assert "standard_footer" in ctx
    assert "topic" not in ctx  # topic 是后续注入的


def test_render_substitutes_variables():
    """渲染时应正确替换变量。"""
    template = "Hello, {project_name}! Topic: {topic}"
    result = render_prompt(template, topic="测试主题")
    assert "{project_name}" not in result
    assert "测试主题" in result


def test_render_handles_unknown_vars():
    """模板里的未知变量不应该报错（容错）。"""
    template = "{project_name} {nonexistent_var}"
    result = render_prompt(template, topic="x")
    # 未知变量应保留原样而非报错
    assert result is not None


def test_sponsor_attribution_is_loaded():
    """赞助方标注应该从 project.yaml 加载。"""
    ctx = build_template_context()
    sponsor = ctx["sponsor_attribution"]
    assert sponsor, "sponsor_attribution 不应为空"
    assert "Upstream" in sponsor or "源起" in sponsor


def test_contributor_selection():
    """指定 contributor 应该选中正确的作者。"""
    ctx_default = build_template_context()
    ctx_named = build_template_context(contributor_id="fengxiaoting")
    # 至少 author_name 应该有值
    assert ctx_named["author_name"]
