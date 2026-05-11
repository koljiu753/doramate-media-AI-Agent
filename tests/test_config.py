"""配置加载相关测试。"""
import pytest
from doramate_agent.utils import (
    get_project_config, get_agent_config, PROJECT_ROOT,
)


def test_project_config_loads():
    """project.yaml 能正常加载且包含必要字段。"""
    cfg = get_project_config()
    assert cfg.get("project.name"), "缺少 project.name"
    assert cfg.get("project.github"), "缺少 project.github"
    

def test_agent_config_loads():
    """agent.yaml 能正常加载。"""
    cfg = get_agent_config()
    assert cfg.get("llm.default_provider"), "缺少 LLM 配置"


def test_dot_path_access():
    """点路径访问应该正常工作。"""
    cfg = get_project_config()
    name = cfg.get("project.name")
    assert name is not None


def test_default_value():
    """不存在的 key 应该返回 default。"""
    cfg = get_project_config()
    assert cfg.get("nonexistent.key.path", "fallback") == "fallback"


def test_project_root_exists():
    """PROJECT_ROOT 应该指向正确的目录。"""
    assert PROJECT_ROOT.exists()
    assert (PROJECT_ROOT / "config" / "project.yaml").exists()
