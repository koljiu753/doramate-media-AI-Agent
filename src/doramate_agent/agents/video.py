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
from ..video.tts import EdgeTTS, resolve_voice
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
        self.style_presets = self.agent_config.get("video.visual_style.presets", {}) or {}
        default_style = self.agent_config.get("video.visual_style.default_preset", "editorial")
        self.visual_style = self._resolve_visual_style(default_style)
        
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
        voice: Optional[str] = None,
        voice_preset: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        style_preset: Optional[str] = None,
        style_hint: Optional[str] = None,
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
            voice: Edge-TTS 原始音色 ID
            voice_preset: 音色预设名
            rate: 语速，如 +8%
            pitch: 音调，如 +0Hz
            style_preset: 视觉风格预设名
            style_hint: 额外审美偏好，会追加到风格锁
        
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

        if style_preset or style_hint:
            default_style = self.agent_config.get("video.visual_style.default_preset", "editorial")
            self.visual_style = self._resolve_visual_style(style_preset or default_style, style_hint=style_hint)

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
        tts = self._make_tts(voice=voice, voice_preset=voice_preset, rate=rate, pitch=pitch)
        audio_paths = tts.synthesize_scenes(script.scenes, audio_dir)
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
            "style_reference": str(production_pack["style_reference"]),
            "review_checklist": str(production_pack["review_checklist"]),
            "next_steps": str(production_pack["next_steps"]),
            "style_guide": str(production_pack["style_guide"]),
            "style_preset": self.visual_style.get("preset", ""),
            "voice": tts.voice,
            "voice_rate": tts.rate,
            "voice_pitch": tts.pitch,
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
        style_reference = work_dir / "STYLE_REFERENCE.md"
        review_checklist = work_dir / "review_checklist.md"
        next_steps = work_dir / "NEXT_STEPS.md"
        style_guide = work_dir / "STYLE_GUIDE.md"

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
            "重要：如果单靠文字提示词效果不好，先按 `STYLE_REFERENCE.md` 生成一张满意的风格母版，然后每个分镜都上传这张母版作为参考图。",
            "",
            "每个分镜都必须复制完整提示词，不要只复制画面描述。完整提示词里已经包含统一风格锁。",
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
                    "### 横屏 16:9（网页版 GPT / 即梦中文短版）",
                    self._landscape_prompt_cn(scene.visual_description),
                    "",
                    f"保存为：`images_landscape/scene_{scene.index:03d}.png`",
                    "",
                    "### 竖屏 9:16",
                    self._portrait_prompt(scene.visual_description),
                    "",
                    "### 竖屏 9:16（网页版 GPT / 即梦中文短版）",
                    self._portrait_prompt_cn(scene.visual_description),
                    "",
                    f"保存为：`images_portrait/scene_{scene.index:03d}.png`",
                    "",
                ]
            )
        if script.thumbnail_prompts:
            prompt_lines.extend(["## 封面提示词", ""])
            for i, prompt in enumerate(script.thumbnail_prompts, 1):
                prompt_lines.extend([f"### 封面 {i}", f"{self._style_lock()} COVER CONTENT: {prompt}", ""])
        prompt_sheet.write_text("\n".join(prompt_lines), encoding="utf-8")

        reference_lines = [
            "# 风格母版生成说明",
            "",
            "用途：解决“单张图不好看”的问题。不要一上来就批量生成所有分镜，先生成 1-2 张风格母版，挑满意后再生成正式分镜。",
            "",
            "## 推荐流程",
            "",
            "1. 复制下面的“风格母版 prompt”去网页版 GPT / 即梦 / 可灵生成一张参考图。",
            "2. 如果不满意，只改审美描述，不要先动分镜内容。",
            "3. 选中满意的一张图，后续每个 Scene 生成时都上传这张图，并写：`请严格参考这张图的画风、色彩、线条、构图密度和质感，只替换画面内容。`",
            "4. 再去 `ai_image_prompts.md` 逐张生成分镜。",
            "",
            "## 风格母版 prompt",
            "",
            self._style_reference_prompt(),
            "",
            "## 分镜生成时的固定开场白",
            "",
            "我已上传一张风格参考图。请严格参考它的画风、色彩、线条、构图密度、质感和光影，只替换为下面这个分镜内容。不要改变整体风格，不要生成真实产品截图，不要生成真实机器人 demo。",
            "",
            "## 如果还是不好看，优先这样改",
            "",
            "- 太像儿童教育图：加 `更克制、更成熟、更像开源社区官网文章头图`",
            "- 太像廉价 PPT：加 `不要模板感，不要素材库图标堆叠，要像完整编辑插画`",
            "- 太乱：加 `只保留一个主视觉隐喻，减少装饰元素，画面留白更多`",
            "- 太假 UI：加 `不要生成可读界面，只用抽象卡片和线条表达信息架构`",
            "- 太赛博/太暗：加 `白色背景，低饱和，日间光线，不要霓虹，不要暗色科幻`",
        ]
        style_reference.write_text("\n".join(reference_lines), encoding="utf-8")

        style_lines = [
            "# 视频视觉风格锁",
            "",
            "这份风格锁用于统一整条视频所有 AI 生图。手动用网页版 GPT/即梦/可灵生图时，也要把这里的风格要求复制进每个分镜。",
            "",
            f"风格名称：{self.visual_style['name']}",
            "",
            "## 固定风格",
            f"- 预设：{self.visual_style.get('preset', '')}",
            f"- 色彩：{self.visual_style['palette']}",
            f"- 构图：{self.visual_style['composition']}",
            f"- 材质：{self.visual_style['material']}",
            f"- 字幕/文字区：{self.visual_style['typography']}",
            f"- 质量标准：{self.visual_style['quality_bar']}",
        "",
            "## 禁用项",
            self.visual_style["negative_prompt"],
            "",
            "## 使用规则",
            "- 同一条视频不要混用照片、3D、赛博朋克、手绘、水彩等多种风格。",
            "- 不要让模型自己设计 DoraMate 真实产品界面，只能生成概念示意图、数据流图、社区学习路线图。",
            "- 如果某张图风格漂移，把提示词里的 STYLE LOCK / consistent visual system 重复到开头和结尾。",
            "- 封面可以更强对比，但仍必须沿用同一套色彩和材质。",
        ]
        style_guide.write_text("\n".join(style_lines), encoding="utf-8")

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
            "style_reference": style_reference,
            "review_checklist": review_checklist,
            "next_steps": next_steps,
            "style_guide": style_guide,
        }

    @staticmethod
    def _md_cell(text: str) -> str:
        return (text or "").replace("|", "\\|").replace("\n", "<br>")

    def _style_lock(self) -> str:
        return (
            f"STYLE LOCK: {self.visual_style['name']}. "
            f"Palette: {self.visual_style['palette']}. "
            f"Composition: {self.visual_style['composition']}. "
            f"Material: {self.visual_style['material']}. "
            f"Typography/subtitle area: {self.visual_style['typography']}. "
            f"Quality bar: {self.visual_style['quality_bar']}. "
            "Design it as one finished editorial illustration, not a rough concept sketch. "
            "Use one clear visual metaphor, strong hierarchy, balanced negative space, precise shapes, and consistent lighting. "
            "Keep the same art direction, colors, line weight, UI shape language, and lighting across all scenes. "
            f"Negative prompt: {self.visual_style['negative_prompt']}."
        )

    def _style_lock_cn(self) -> str:
        return (
            f"统一风格锁：{self.visual_style['name']}。"
            f"色彩：{self.visual_style['palette']}。"
            f"构图：{self.visual_style['composition']}。"
            f"材质：{self.visual_style['material']}。"
            f"字幕安全区：{self.visual_style['typography']}。"
            f"质量标准：{self.visual_style['quality_bar']}。"
            "画面必须像一张完成度高的开源社区编辑插画，不要像临时概念草图。"
            "只保留一个清晰主视觉隐喻，层次明确，留白充足，线条和光影统一。"
            f"禁止：{self.visual_style['negative_prompt']}。"
        )

    def _landscape_prompt(self, text: str) -> str:
        return (
            f"{self._style_lock()} SCENE CONTENT: {text}. "
            "Aspect ratio 16:9 horizontal. Clear focal subject, cinematic but clean crop, generous whitespace, bottom safe area for Chinese subtitles. "
            "No small text, no decorative filler, no random icons."
        )

    def _landscape_prompt_cn(self, text: str) -> str:
        return (
            f"{self._style_lock_cn()} "
            f"分镜内容：{text}。"
            "横屏 16:9。主体清楚，构图干净，底部留出中文字幕区域。"
            "不要小字，不要随机图标，不要装饰性填充。"
        )

    def _portrait_prompt(self, text: str) -> str:
        return (
            f"{self._style_lock()} SCENE CONTENT: {text}. "
            "Aspect ratio 9:16 vertical. Mobile-first composition, large central subject, clear top-to-bottom reading order, bottom safe area for Chinese subtitles. "
            "No small text, no decorative filler, no random icons."
        )

    def _portrait_prompt_cn(self, text: str) -> str:
        return (
            f"{self._style_lock_cn()} "
            f"分镜内容：{text}。"
            "竖屏 9:16。手机优先构图，主体更大，上下阅读顺序清楚，底部留出中文字幕区域。"
            "不要小字，不要随机图标，不要装饰性填充。"
        )

    def _style_reference_prompt(self) -> str:
        return (
            f"{self._style_lock_cn()} "
            "请生成一张“DoraCN / dora-rs 新手学习路线”的风格母版图，不作为最终分镜，只用于确定画风。"
            "画面内容：白色开源社区学习空间，一条从左到右的学习路线，三个抽象阶段节点：认识 dora-rs、跑通 quick-start、加入中文社区；"
            "中间有一个简洁的数据流/路线图主视觉，周围只有少量代码卡片、文档卡片和社区标记。"
            "不要出现真实人物，不要真实机器人，不要可读产品界面，不要生成 DoraMate 已上线 UI。"
            "整体要成熟、克制、清爽，像正式开源社区官网文章头图。"
        )

    def _resolve_visual_style(self, preset: str, style_hint: Optional[str] = None) -> dict[str, str]:
        preset_data = self.style_presets.get(preset)
        if not preset_data:
            available = ", ".join(sorted(self.style_presets)) or "(none)"
            raise ValueError(f"未知视觉风格预设：{preset}。可选：{available}")
        style = {
            "preset": preset,
            "name": preset_data.get("name", preset),
            "palette": preset_data.get("palette", ""),
            "composition": preset_data.get("composition", ""),
            "material": preset_data.get("material", ""),
            "typography": preset_data.get("typography", ""),
            "quality_bar": preset_data.get("quality_bar", ""),
            "negative_prompt": preset_data.get("negative_prompt", ""),
        }
        if style_hint:
            style["quality_bar"] = f"{style['quality_bar']}; user preference: {style_hint}"
        return style

    def _make_tts(
        self,
        voice: Optional[str] = None,
        voice_preset: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
    ) -> EdgeTTS:
        cfg_voice = self.agent_config.get("video.tts.voice_zh", "zh-CN-XiaoxiaoNeural")
        cfg_rate = self.agent_config.get("video.tts.rate", "+0%")
        cfg_pitch = self.agent_config.get("video.tts.pitch", "+0Hz")
        if voice:
            resolved_voice = voice
        elif voice_preset:
            resolved_voice = resolve_voice(voice_preset)
        else:
            resolved_voice = cfg_voice
        return EdgeTTS(
            voice=resolved_voice,
            rate=rate or cfg_rate,
            pitch=pitch or cfg_pitch,
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
