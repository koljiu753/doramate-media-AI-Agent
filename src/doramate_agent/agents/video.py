"""
视频 Agent

端到端：主题 → 完整视频 + 多平台简介

工作流：
  1. ScriptGenerator    → 脚本 + 分镜
  2. EdgeTTS            → 每个分镜的口播音频
  3. ImageGenerator     → 每个分镜的画面（占位图 / AI 生图）
  4. SubtitleGenerator  → SRT 字幕
  5. VideoComposer      → FFmpeg 合成成片

输出：
  - {topic}.mp4
  - {topic}_竖屏.mp4 (小红书版)
  - {topic}_metadata.json (标题/简介/封面 prompt)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import BaseAgent
from ..video.script import ScriptGenerator, VideoScript
from ..video.tts import EdgeTTS
from ..video.subtitles import generate_srt
from ..video.image_gen import PlaceholderImageGenerator, DEFAULT_LANDSCAPE, DEFAULT_PORTRAIT
from ..video.composer import VideoComposer, check_ffmpeg
from ..utils import PROJECT_ROOT

logger = logging.getLogger(__name__)


class VideoAgent(BaseAgent):
    """视频 Agent。"""

    agent_name = "video"

    def __init__(self):
        super().__init__()
        self.script_gen = ScriptGenerator()
        
        # 从配置读 TTS 参数
        tts_voice = self.agent_config.get("video.tts.voice_zh", "zh-CN-XiaoxiaoNeural")
        tts_rate = self.agent_config.get("video.tts.rate", "+0%")
        tts_pitch = self.agent_config.get("video.tts.pitch", "+0Hz")
        self.tts = EdgeTTS(voice=tts_voice, rate=tts_rate, pitch=tts_pitch)
        
        self.image_gen = PlaceholderImageGenerator()

    def run(
        self,
        topic: str,
        user_hint: str = "",
        target_duration: int = 180,
        platforms: Optional[list[str]] = None,
        bgm_path: Optional[Path] = None,
        skip_landscape: bool = False,
        skip_portrait: bool = False,
    ) -> dict:
        """
        端到端生成视频。
        
        Args:
            topic: 视频主题
            user_hint: 给脚本生成的额外提示
            target_duration: 目标时长（秒）
            platforms: 目标平台 ["bilibili", "xiaohongshu_video"]
            bgm_path: 背景音乐文件路径
            skip_landscape: 跳过 16:9 横屏版（B站）
            skip_portrait: 跳过 9:16 竖屏版（小红书）
        
        Returns:
            dict: 包含所有产物的路径
        """
        if not check_ffmpeg():
            raise RuntimeError(
                "未找到 ffmpeg，无法合成视频。安装方法：\n"
                "  Ubuntu: sudo apt install ffmpeg\n"
                "  macOS:  brew install ffmpeg\n"
                "  Windows: https://ffmpeg.org/download.html"
            )

        # === 任务工作目录 ===
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        task_slug = topic.replace(" ", "_").replace("/", "_")[:30]
        work_dir = self.get_output_dir() / f"{timestamp}_{task_slug}"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 工作目录：{work_dir}")
        
        # === 步骤 1：生成脚本 ===
        logger.info("🎬 [1/5] 生成视频脚本...")
        script = self.script_gen.generate(
            topic=topic,
            user_hint=user_hint,
            target_duration=target_duration,
        )
        # 保存脚本 JSON 备查
        script_json_path = work_dir / "script.json"
        script_json_path.write_text(
            json.dumps(script.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"  ✓ 脚本已生成（{len(script.scenes)} 个分镜，总时长 ~{script.total_duration:.0f}秒）")

        # === 步骤 2：TTS 生成口播 ===
        logger.info("🎙️  [2/5] 合成口播音频（Edge-TTS，免费）...")
        audio_dir = work_dir / "audio"
        audio_paths = self.tts.synthesize_scenes(script.scenes, audio_dir)
        logger.info(f"  ✓ 已生成 {len(audio_paths)} 段音频")

        # === 步骤 3：生成图片（占位图）===
        logger.info("🎨 [3/5] 生成画面（占位图模式）...")
        logger.info("  ⚠️  当前用占位图。要换真实 AI 生图，请看 docs/CUSTOMIZE_IMAGE_GEN.md")
        
        outputs = {
            "work_dir": str(work_dir),
            "script_json": str(script_json_path),
            "title": script.selected_title,
            "title_candidates": script.title_candidates,
            "description": script.description,
            "thumbnail_prompts": script.thumbnail_prompts,
        }

        # === 步骤 4-5：合成横屏版（B站） ===
        if not skip_landscape:
            logger.info("🎞️  [4/5] 合成横屏版（B站，1920x1080）...")
            landscape_image_dir = work_dir / "images_landscape"
            landscape_images = self.image_gen.generate_for_scenes(
                script.scenes, landscape_image_dir, size=DEFAULT_LANDSCAPE
            )
            
            srt_landscape = work_dir / "subtitles.srt"
            generate_srt(script.scenes, audio_paths, srt_landscape)
            
            composer_landscape = VideoComposer(target_size=DEFAULT_LANDSCAPE)
            landscape_path = work_dir / f"{task_slug}_横屏_bilibili.mp4"
            composer_landscape.compose(
                image_paths=landscape_images,
                audio_paths=audio_paths,
                scene_durations=[s.duration_seconds for s in script.scenes],
                output_path=landscape_path,
                srt_path=srt_landscape,
                bgm_path=bgm_path,
            )
            outputs["video_landscape"] = str(landscape_path)
            logger.info(f"  ✓ 横屏版完成：{landscape_path}")

        # === 步骤 5：合成竖屏版（小红书） ===
        if not skip_portrait:
            logger.info("📱 [5/5] 合成竖屏版（小红书，1080x1920）...")
            portrait_image_dir = work_dir / "images_portrait"
            portrait_images = self.image_gen.generate_for_scenes(
                script.scenes, portrait_image_dir, size=DEFAULT_PORTRAIT
            )
            
            srt_portrait = work_dir / "subtitles_portrait.srt"
            if not srt_portrait.exists():
                generate_srt(script.scenes, audio_paths, srt_portrait)
            
            composer_portrait = VideoComposer(target_size=DEFAULT_PORTRAIT)
            portrait_path = work_dir / f"{task_slug}_竖屏_xiaohongshu.mp4"
            composer_portrait.compose(
                image_paths=portrait_images,
                audio_paths=audio_paths,
                scene_durations=[s.duration_seconds for s in script.scenes],
                output_path=portrait_path,
                srt_path=srt_portrait,
                bgm_path=bgm_path,
            )
            outputs["video_portrait"] = str(portrait_path)
            logger.info(f"  ✓ 竖屏版完成：{portrait_path}")

        # === 保存最终元数据 ===
        metadata_path = work_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(outputs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        outputs["metadata"] = str(metadata_path)

        logger.info(f"\n🎉 视频生产完成！全部产物在：{work_dir}")
        return outputs
