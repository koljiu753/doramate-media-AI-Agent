"""平台插件加载测试。"""
import pytest
from doramate_agent.platforms import get_platform_registry, get_platform


def test_platforms_load():
    """所有 5 个内置平台都能加载。"""
    registry = get_platform_registry()
    plugins = registry.list_all()
    plugin_ids = {p.id for p in plugins}
    
    expected = {"csdn", "xiaohongshu", "zhihu", "bilibili", "wechat"}
    missing = expected - plugin_ids
    assert not missing, f"缺少平台插件：{missing}"


def test_platform_attributes():
    """每个平台都应有必要的属性。"""
    registry = get_platform_registry()
    for plugin in registry.list_all():
        assert plugin.id, f"平台缺少 id"
        assert plugin.name, f"{plugin.id} 缺少 name"
        assert plugin.prompt_template, f"{plugin.id} 缺少 prompt_template"


def test_platform_prompt_files_exist():
    """每个平台的 prompt 文件应该存在。"""
    registry = get_platform_registry()
    for plugin in registry.list_all():
        path = plugin.prompt_file_path
        assert path.exists(), f"{plugin.id} 的 prompt 文件不存在：{path}"


def test_unknown_platform_raises():
    """未知平台应该抛出 KeyError。"""
    with pytest.raises(KeyError):
        get_platform("nonexistent_platform_xyz")
