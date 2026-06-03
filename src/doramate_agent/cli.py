"""
DoraMate Agent CLI

统一命令行入口。设计为子命令风格（git-like）：
    doramate-agent create   --topic "..."          # 创作 5 平台内容
    doramate-agent video    --topic "..."          # 生成视频
    doramate-agent topics                          # 选题推荐
    doramate-agent report                          # 生成周报
    doramate-agent doctor                          # 健康检查
    doramate-agent --help

也可以直接 python -m doramate_agent ...
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """初始化日志。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_create(args):
    """创作 Agent 子命令。"""
    from .agents import CreatorAgent

    agent = CreatorAgent()
    platforms = args.platforms.split(",") if args.platforms else None
    result = agent.run(
        topic=args.topic,
        platforms=platforms,
        user_hint=args.hint,
        contributor_id=args.contributor,
    )

    print("\n" + "=" * 60)
    print(f"✅ 创作完成 | 共 {result.success_count}/{len(result.results)} 个平台")
    print(f"💰 累计成本：¥{result.total_cost_cny:.4f} | Tokens：{result.total_tokens}")
    print("=" * 60)
    for r in result.results:
        status = "✓" if r.success else "✗"
        print(f"  {status} {r.platform_name:8s} → {r.file_path.name if r.success else r.error}")


def cmd_video(args):
    """视频 Agent 子命令。"""
    from .agents import VideoAgent

    agent = VideoAgent()
    bgm = Path(args.bgm) if args.bgm else None
    
    outputs = agent.run(
        topic=args.topic,
        user_hint=args.hint,
        target_duration=args.duration,
        bgm_path=bgm,
        skip_landscape=args.no_landscape,
        skip_portrait=args.no_portrait,
        voice=args.voice,
        voice_preset=args.voice_preset,
        rate=args.rate,
        pitch=args.pitch,
        style_preset=args.style_preset,
        style_hint=args.style_hint,
    )
    
    print("\n" + "=" * 60)
    print("🎬 视频产出清单")
    print("=" * 60)
    print(f"📁 工作目录：{outputs['work_dir']}")
    print(f"🎬 标题：{outputs['title']}")
    print(f"🎙️  音色：{outputs.get('voice', '?')} | rate={outputs.get('voice_rate', '?')} | pitch={outputs.get('voice_pitch', '?')}")
    print(f"📝 简介：\n{outputs['description'][:200]}...")
    if outputs.get("style_guide"):
        print(f"🎨 风格锁：{outputs['style_guide']}")
    if outputs.get("style_preset"):
        print(f"🧭 视觉预设：{outputs['style_preset']}")
    if outputs.get("image_prompt_sheet"):
        print(f"🖼️  生图提示词：{outputs['image_prompt_sheet']}")
    if "video_landscape" in outputs:
        print(f"🎞️  B 站横屏版：{outputs['video_landscape']}")
    if "video_portrait" in outputs:
        print(f"📱 小红书竖屏版：{outputs['video_portrait']}")
    print()
    print("💡 下一步：")
    print(f"  - 替换占位图为真实 AI 生图：编辑 {outputs['work_dir']}/images_landscape/*.png")
    print(f"  - 然后重跑视频合成（功能待实现，可手动用 ffmpeg）")
    print(f"  - 封面 prompt（可拿到 Midjourney/DALL-E 生成）：")
    for i, p in enumerate(outputs.get("thumbnail_prompts", []), 1):
        print(f"    [{i}] {p}")


def cmd_voices(args):
    """列出推荐音色，必要时也可以在线查询 Edge-TTS 完整音色。"""
    from .video.tts import EdgeTTS, RECOMMENDED_VOICES
    import asyncio

    print("\n推荐音色预设：")
    for name, voice in RECOMMENDED_VOICES.items():
        print(f"  {name:12s} {voice}")

    if args.online:
        print("\nEdge-TTS 在线音色列表：")
        voices = asyncio.run(EdgeTTS.list_voices(language=args.language))
        for item in voices:
            print(f"  {item.get('ShortName')} | {item.get('Gender')} | {item.get('FriendlyName')}")


def cmd_styles(args):
    """列出视频生图风格预设。"""
    from .utils import get_agent_config

    cfg = get_agent_config()
    presets = cfg.get("video.visual_style.presets", {}) or {}
    default_preset = cfg.get("video.visual_style.default_preset", "")
    print("\n视频视觉风格预设：")
    for name, data in presets.items():
        marker = " (default)" if name == default_preset else ""
        print(f"\n  {name}{marker}")
        print(f"    {data.get('name', '')}")
        print(f"    {data.get('quality_bar', '')}")


def cmd_recompose(args):
    """用已替换的分镜图片重新合成视频。"""
    from .agents import VideoAgent

    agent = VideoAgent()
    bgm = Path(args.bgm) if args.bgm else None
    outputs = agent.recompose(
        work_dir=Path(args.work_dir),
        bgm_path=bgm,
        skip_landscape=args.no_landscape,
        skip_portrait=args.no_portrait,
    )

    print("\n" + "=" * 60)
    print("🎞️  视频重合成完成")
    print("=" * 60)
    if "video_landscape" in outputs:
        print(f"🎞️  B 站横屏版：{outputs['video_landscape']}")
    if "video_portrait" in outputs:
        print(f"📱 小红书竖屏版：{outputs['video_portrait']}")


def cmd_web(args):
    """启动内置 Web UI。"""
    from .web.server import run_server

    return run_server(host=args.host, port=args.port)


def cmd_doctor(args):
    """健康检查：所有依赖、配置、API Key 是否就绪。"""
    print("\n" + "=" * 60)
    print("🩺 DoraMate Agent 健康检查")
    print("=" * 60)
    
    issues = []
    
    # 1. 配置文件
    print("\n📋 [1/5] 检查配置文件...")
    try:
        from .utils import get_project_config, get_agent_config
        proj = get_project_config()
        agent_cfg = get_agent_config()
        print(f"  ✓ project.yaml: {proj.get('project.name', '?')}")
        print(f"  ✓ agent.yaml: LLM={agent_cfg.get('llm.default_provider')}")
    except Exception as e:
        issues.append(f"配置加载失败：{e}")
        print(f"  ✗ {e}")

    # 2. .env / API Key
    print("\n🔑 [2/5] 检查 API Key...")
    try:
        from .utils import get_secret
        provider = agent_cfg.get("llm.default_provider", "deepseek")
        key_name = f"{provider.upper()}_API_KEY"
        key = get_secret(key_name)
        print(f"  ✓ {key_name}: {'*' * 20}{key[-4:] if key else '(空)'}")
    except Exception as e:
        issues.append(f"API Key 缺失：{e}")
        print(f"  ✗ {e}")

    # 3. LLM 连接性
    print("\n🤖 [3/5] 测试 LLM 调用...")
    try:
        from .llm import get_llm
        llm = get_llm()
        if llm.health_check():
            print(f"  ✓ {llm.provider_name} 工作正常")
        else:
            issues.append("LLM 健康检查失败")
            print(f"  ✗ LLM 健康检查失败")
    except Exception as e:
        issues.append(f"LLM 调用错误：{e}")
        print(f"  ✗ {e}")

    # 4. 平台插件
    print("\n📱 [4/5] 检查平台插件...")
    try:
        from .platforms import get_platform_registry
        registry = get_platform_registry()
        plugins = registry.list_all()
        print(f"  ✓ 已加载 {len(plugins)} 个平台插件")
        for p in plugins:
            status = "✓" if p.enabled else "⊘"
            print(f"    {status} {p.id} ({p.name})")
    except Exception as e:
        issues.append(f"平台插件错误：{e}")
        print(f"  ✗ {e}")

    # 5. 视频依赖（FFmpeg）
    print("\n🎬 [5/5] 检查视频生成依赖...")
    try:
        from .video.composer import get_ffmpeg_path
        ffmpeg_bin = get_ffmpeg_path()
        if ffmpeg_bin:
            print(f"  ✓ FFmpeg 已找到：{ffmpeg_bin}")
        else:
            issues.append("FFmpeg 未安装（视频功能不可用）")
            print("  ⚠️  FFmpeg 未安装。三种方案：")
            print("     A) 把 ffmpeg.exe 所在目录加到系统 PATH（推荐）")
            print("     B) 在 .env 里设 FFMPEG_PATH=完整路径")
            print("     C) 放到 C:\\ffmpeg\\bin\\ 或 D:\\ffmpeg\\bin\\")
    except ImportError:
        print("  ⚠️  视频模块未导入")
    
    # 总结
    print("\n" + "=" * 60)
    if not issues:
        print("✅ 一切就绪！可以开始用 Agent 了。")
    else:
        print(f"⚠️  发现 {len(issues)} 个问题：")
        for i in issues:
            print(f"  • {i}")
    print("=" * 60)
    return 0 if not issues else 1


def cmd_topics(args):
    """选题 Agent（占位，Phase 2 实现）"""
    print("⏳ 选题 Agent（Phase 2）尚未实现，敬请期待。")
    print("   Phase 1 已实现：create、video、doctor")
    return 0


def cmd_report(args):
    """周报 Agent（占位，Phase 4 实现）"""
    print("⏳ 周报 Agent（Phase 4）尚未实现，敬请期待。")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="doramate-agent",
        description="DoraMate 宣传 Agent · 开源内容自动化工具",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="创作多平台内容")
    p_create.add_argument("--topic", required=True, help="内容主题")
    p_create.add_argument("--platforms", help="逗号分隔的平台 ID（默认全部）")
    p_create.add_argument("--hint", default="", help="额外提示")
    p_create.add_argument("--contributor", help="作者 ID（来自 project.yaml）")
    p_create.set_defaults(func=cmd_create)

    # video
    p_video = subparsers.add_parser("video", help="生成视频（脚本+TTS+剪辑）")
    p_video.add_argument("--topic", required=True, help="视频主题")
    p_video.add_argument("--hint", default="", help="额外提示")
    p_video.add_argument("--duration", type=int, default=180, help="目标时长（秒）")
    p_video.add_argument("--bgm", help="背景音乐文件路径（可选）")
    p_video.add_argument("--no-landscape", action="store_true", help="跳过横屏版（B站）")
    p_video.add_argument("--no-portrait", action="store_true", help="跳过竖屏版（小红书）")
    p_video.add_argument("--voice-preset", help="音色预设：default/professional/warm/energetic/documentary")
    p_video.add_argument("--voice", help="Edge-TTS 原始音色 ID，例如 zh-CN-YunxiNeural")
    p_video.add_argument("--rate", help="语速，例如 +8%% 或 -5%%")
    p_video.add_argument("--pitch", help="音调，例如 +0Hz")
    p_video.add_argument("--style-preset", help="视觉风格预设：editorial/isometric/screenflow/bold_cover")
    p_video.add_argument("--style-hint", help="额外审美偏好，例如：更像成熟开源社区官网插画，不要儿童教育感")
    p_video.set_defaults(func=cmd_video)

    # voices
    p_voices = subparsers.add_parser("voices", help="列出可用 TTS 音色")
    p_voices.add_argument("--online", action="store_true", help="在线查询 Edge-TTS 完整音色列表")
    p_voices.add_argument("--language", default="zh-CN", help="语言过滤，例如 zh-CN")
    p_voices.set_defaults(func=cmd_voices)

    # styles
    p_styles = subparsers.add_parser("styles", help="列出视频生图风格预设")
    p_styles.set_defaults(func=cmd_styles)

    # recompose
    p_recompose = subparsers.add_parser("recompose", help="替换 AI 图片后重新合成视频")
    p_recompose.add_argument("--work-dir", required=True, help="video 命令生成的工作目录")
    p_recompose.add_argument("--bgm", help="背景音乐文件路径（可选）")
    p_recompose.add_argument("--no-landscape", action="store_true", help="跳过横屏版（B站）")
    p_recompose.add_argument("--no-portrait", action="store_true", help="跳过竖屏版（小红书）")
    p_recompose.set_defaults(func=cmd_recompose)

    # web
    p_web = subparsers.add_parser("web", help="启动浏览器 Web UI（手机/电脑可用）")
    p_web.add_argument("--host", default="127.0.0.1", help="监听地址；手机访问用 0.0.0.0")
    p_web.add_argument("--port", type=int, default=8501, help="监听端口")
    p_web.set_defaults(func=cmd_web)

    # topics（占位）
    p_topics = subparsers.add_parser("topics", help="选题推荐（Phase 2）")
    p_topics.set_defaults(func=cmd_topics)

    # report（占位）
    p_report = subparsers.add_parser("report", help="生成周报（Phase 4）")
    p_report.set_defaults(func=cmd_report)

    # doctor
    p_doctor = subparsers.add_parser("doctor", help="健康检查")
    p_doctor.set_defaults(func=cmd_doctor)

    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
