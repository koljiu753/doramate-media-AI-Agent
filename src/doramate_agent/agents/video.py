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
from ..video.script import ScriptGenerator, VideoScript, Scene
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
        production_pack = self._write_production_pack(script, work_dir)
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
            "script_markdown": str(production_pack["script_markdown"]),
            "image_prompt_sheet": str(production_pack["image_prompt_sheet"]),
            "review_checklist": str(production_pack["review_checklist"]),
            "next_steps": str(production_pack["next_steps"]),
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

    def _write_production_pack(self, script: VideoScript, work_dir: Path) -> dict[str, Path]:
        """写出人工可读的视频生产包。"""
        script_md = work_dir / "video_script.md"
        prompt_sheet = work_dir / "ai_image_prompts.md"
        review_checklist = work_dir / "review_checklist.md"
        next_steps = work_dir / "NEXT_STEPS.md"

        script_lines = [
            f"# {script.selected_title}",
            "",
            "## 标题备选",
            *[f"- {title}" for title in script.title_candidates],
            "",
            "## 视频简介",
            script.description,
            "",
            "## 分镜脚本",
            "",
            "| 场景 | 时长 | 屏幕文字 | 口播 | 画面描述 |",
            "|---|---:|---|---|---|",
        ]
        for scene in script.scenes:
            script_lines.append(
                "| {index} | {duration:g}s | {text} | {narration} | {visual} |".format(
                    index=scene.index,
                    duration=scene.duration_seconds,
                    text=self._md_cell(scene.on_screen_text),
                    narration=self._md_cell(scene.narration),
                    visual=self._md_cell(scene.visual_description),
                )
            )
        script_md.write_text("\n".join(script_lines), encoding="utf-8")

        prompt_lines = [
            "# AI 生图提示词清单",
            "",
            "用途：把每个分镜的提示词复制到即梦、可灵、Midjourney、DALL-E 等工具生成图片。",
            "",
            "生成后覆盖对应文件：",
            "- 横屏：`images_landscape/scene_001.png`、`scene_002.png` ...",
            "- 竖屏：`images_portrait/scene_001.png`、`scene_002.png` ...",
            "",
            "建议：横屏使用 16:9，竖屏使用 9:16；不要生成 DoraMate 已上线产品 UI，不要生成真实硬件 demo。",
            "",
        ]
        for scene in script.scenes:
            prompt_lines.extend(
                [
                    f"## Scene {scene.index:03d}",
                    "",
                    f"屏幕文字：{scene.on_screen_text or '无'}",
                    "",
                    "### 横屏 16:9",
                    self._landscape_prompt(scene.visual_description),
                    "",
                    f"保存为：`images_landscape/scene_{scene.index:03d}.png`",
                    "",
                    "### 竖屏 9:16",
                    self._portrait_prompt(scene.visual_description),
                    "",
                    f"保存为：`images_portrait/scene_{scene.index:03d}.png`",
                    "",
                ]
            )
        if script.thumbnail_prompts:
            prompt_lines.extend(["## 封面提示词", ""])
            for i, prompt in enumerate(script.thumbnail_prompts, 1):
                prompt_lines.extend([f"### 封面 {i}", prompt, ""])
        prompt_sheet.write_text("\n".join(prompt_lines), encoding="utf-8")

        checklist_lines = [
            "# 发布前审核清单",
            "",
            "## 事实安全",
            "- [ ] 没有写“打开 DoraMate 网页版”",
            "- [ ] 没有写“拖拽节点已经能跑起来”",
            "- [ ] 没有写“节点市场 / 一键部署 / 实时监控已实现”",
            "- [ ] 没有写“机器人真实动了”或真实硬件 demo",
            "- [ ] 没有把 dora-rs 的能力写成 DoraMate 已实现功能",
            "- [ ] 没有虚构采访、用户反馈、团队合影或发布会现场",
            "",
            "## 身份与标注",
            "- [ ] 冯小婷身份保持为产品/UX 设计师、项目执行成员",
            "- [ ] 没有写成学生、算法工程师、ROS 老用户或 dora-rs 维护者",
            "- [ ] 已标注：源起之道支持｜Supported by Upstream Labs",
            "",
            "## 视频质量",
            "- [ ] 字幕没有遮挡主体",
            "- [ ] 竖屏版本文字在手机上可读",
            "- [ ] 每个分镜画面与口播一致",
            "- [ ] 封面标题不夸大、不虚构产品能力",
            "",
            "## 发布链接",
            "- [ ] DoraMate：https://github.com/DoraCN/DoraMate",
            "- [ ] Agent：https://github.com/koljiu753/doramate-media-AI-Agent",
            "- [ ] Dora 中文社区：https://koljiu753.github.io/dora-cn/",
        ]
        review_checklist.write_text("\n".join(checklist_lines), encoding="utf-8")

        next_lines = [
            "# 下一步操作",
            "",
            "1. 检查 `video_script.md`，确认脚本没有事实风险。",
            "2. 打开 `ai_image_prompts.md`，复制每个 Scene 的横屏/竖屏提示词去 AI 生图工具。",
            "3. 把生成图片覆盖到 `images_landscape/` 和 `images_portrait/`。",
            "4. 运行：",
            "",
            "```powershell",
            f'doramate-agent recompose --work-dir "{work_dir}"',
            "```",
            "",
            "5. 按 `review_checklist.md` 做发布前检查。",
        ]
        next_steps.write_text("\n".join(next_lines), encoding="utf-8")

        return {
            "script_markdown": script_md,
            "image_prompt_sheet": prompt_sheet,
            "review_checklist": review_checklist,
            "next_steps": next_steps,
        }

    @staticmethod
    def _md_cell(text: str) -> str:
        return (text or "").replace("|", "\\|").replace("\n", "<br>")

    @staticmethod
    def _landscape_prompt(text: str) -> str:
        return (
            f"{text}. 16:9 horizontal composition, clean technology explainer style, "
            "modern Chinese open-source community visual, clear focal subject, no fake product UI, "
            "no real robot hardware demo, leave safe space for Chinese subtitles at the bottom."
        )

    @staticmethod
    def _portrait_prompt(text: str) -> str:
        return (
            f"{text}. 9:16 vertical composition for short video, clean technology explainer style, "
            "large readable central subject, mobile-first layout, no fake product UI, "
            "no real robot hardware demo, leave safe space for Chinese subtitles at the bottom."
        )

    def recompose(
        self,
        work_dir: Path,
        bgm_path: Optional[Path] = None,
        skip_landscape: bool = False,
        skip_portrait: bool = False,
    ) -> dict:
        """
        用工作目录里的脚本、音频和图片重新合成视频。

        典型用法:
        1. 先运行 `doramate-agent video ...`
        2. 用 AI 生图工具按 `script.json` 里的 visual_description 生成图片
        3. 覆盖 `images_landscape/scene_001.png` 等文件
        4. 运行 `doramate-agent recompose --work-dir ...`
        """
        work_dir = Path(work_dir)
        script_json_path = work_dir / "script.json"
        if not script_json_path.exists():
            raise FileNotFoundError(f"未找到脚本文件：{script_json_path}")
        if not check_ffmpeg():
            raise RuntimeError("未找到 ffmpeg，无法合成视频。")

        data = json.loads(script_json_path.read_text(encoding="utf-8"))
        scenes = [Scene(**s) for s in data.get("scenes", [])]
        task_slug = work_dir.name.split("_", 2)[-1] if "_" in work_dir.name else work_dir.name
        audio_paths = sorted((work_dir / "audio").glob("scene_*.mp3"))
        if len(audio_paths) != len(scenes):
            raise RuntimeError(
                f"音频数量与分镜数量不匹配：audio={len(audio_paths)}, scenes={len(scenes)}"
            )

        outputs = {"work_dir": str(work_dir), "script_json": str(script_json_path)}

        if not skip_landscape:
            landscape_images = sorted((work_dir / "images_landscape").glob("scene_*.png"))
            if len(landscape_images) != len(scenes):
                raise RuntimeError(
                    f"横屏图片数量与分镜数量不匹配：images={len(landscape_images)}, scenes={len(scenes)}"
                )
            srt_landscape = work_dir / "subtitles.srt"
            generate_srt(scenes, audio_paths, srt_landscape)
            landscape_path = work_dir / f"{task_slug}_横屏_bilibili_recomposed.mp4"
            VideoComposer(target_size=DEFAULT_LANDSCAPE).compose(
                image_paths=landscape_images,
                audio_paths=audio_paths,
                scene_durations=[s.duration_seconds for s in scenes],
                output_path=landscape_path,
                srt_path=srt_landscape,
                bgm_path=bgm_path,
            )
            outputs["video_landscape"] = str(landscape_path)

        if not skip_portrait:
            portrait_images = sorted((work_dir / "images_portrait").glob("scene_*.png"))
            if len(portrait_images) != len(scenes):
                raise RuntimeError(
                    f"竖屏图片数量与分镜数量不匹配：images={len(portrait_images)}, scenes={len(scenes)}"
                )
            srt_portrait = work_dir / "subtitles_portrait.srt"
            generate_srt(scenes, audio_paths, srt_portrait)
            portrait_path = work_dir / f"{task_slug}_竖屏_xiaohongshu_recomposed.mp4"
            VideoComposer(target_size=DEFAULT_PORTRAIT).compose(
                image_paths=portrait_images,
                audio_paths=audio_paths,
                scene_durations=[s.duration_seconds for s in scenes],
                output_path=portrait_path,
                srt_path=srt_portrait,
                bgm_path=bgm_path,
            )
            outputs["video_portrait"] = str(portrait_path)

        metadata_path = work_dir / "recompose_metadata.json"
        metadata_path.write_text(json.dumps(outputs, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["metadata"] = str(metadata_path)
        return outputs
