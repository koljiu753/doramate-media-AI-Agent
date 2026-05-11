"""
示例：调用视频 Agent 端到端生成视频

运行：
    python examples/example_video.py
    
要求：
    - DEEPSEEK_API_KEY 已配置
    - 系统安装了 ffmpeg
"""
import logging
from pathlib import Path

from doramate_agent.agents import VideoAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    agent = VideoAgent()
    
    outputs = agent.run(
        topic="什么是 dora-rs？3 分钟极简介绍",
        user_hint="科普向，假设观众没听过 dora-rs，用类比降低门槛",
        target_duration=180,
    )
    
    print("\n" + "=" * 60)
    print("🎬 视频生成完成")
    print("=" * 60)
    print(f"工作目录：{outputs['work_dir']}")
    print(f"标题：{outputs['title']}")
    print(f"\n3 个备选标题：")
    for i, title in enumerate(outputs.get("title_candidates", []), 1):
        print(f"  {i}. {title}")
    
    print(f"\n📺 B 站横屏：{outputs.get('video_landscape', '未生成')}")
    print(f"📱 小红书竖屏：{outputs.get('video_portrait', '未生成')}")
    
    print(f"\n💡 封面图 prompt（拿去 Midjourney/DALL-E 生成）：")
    for i, p in enumerate(outputs.get("thumbnail_prompts", []), 1):
        print(f"  [{i}] {p}")


def script_only_example():
    """只生成脚本，不渲染视频（节省时间，先看脚本质量）"""
    from doramate_agent.video import ScriptGenerator
    
    gen = ScriptGenerator()
    script = gen.generate(
        topic="为什么 dora-rs 比 ROS 2 更适合具身智能",
        user_hint="对比性内容，要有观点",
    )
    
    print(f"标题候选：")
    for t in script.title_candidates:
        print(f"  - {t}")
    print(f"\n推荐标题：{script.selected_title}")
    print(f"\n简介：{script.description}\n")
    print(f"分镜数：{len(script.scenes)}")
    print(f"总时长：{script.total_duration}秒")
    
    for scene in script.scenes[:3]:
        print(f"\n--- 分镜 {scene.index} ({scene.duration_seconds}s) ---")
        print(f"画面：{scene.visual_description}")
        print(f"口播：{scene.narration}")


if __name__ == "__main__":
    # 默认跑完整流程
    main()
    
    # 想只看脚本，注释掉上面，取消下面注释
    # script_only_example()
