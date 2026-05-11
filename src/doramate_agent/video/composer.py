"""
视频合成（FFmpeg 后端）

把：图片序列 + 音频 + 字幕 → 拼成成片视频

为什么用 FFmpeg：
- 开源、免费、跨平台
- 性能比纯 Python 库（如 moviepy）好得多
- 命令行可控，无 GUI 依赖

依赖：
- 系统需安装 ffmpeg（apt install ffmpeg / brew install ffmpeg / 官网下载）
- 也可以在 .env 里设置 FFMPEG_PATH=完整路径（不需要改系统 PATH）
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> Optional[str]:
    """
    定位 ffmpeg 可执行文件。
    
    查找顺序：
        1. 环境变量 FFMPEG_PATH（在 .env 中配置）
        2. 系统 PATH（用 shutil.which）
        3. 常见安装位置（Windows 兜底）
    """
    # 1. 环境变量优先
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists() and p.is_file():
            return str(p)
        logger.warning(f"FFMPEG_PATH 指向的文件不存在：{env_path}")
    
    # 2. 系统 PATH
    found = shutil.which("ffmpeg")
    if found:
        return found
    
    # 3. Windows 常见位置兜底
    common_windows_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"D:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in common_windows_paths:
        if Path(p).exists():
            return p
    
    return None


def check_ffmpeg() -> bool:
    """检查系统是否有可用的 ffmpeg。"""
    return get_ffmpeg_path() is not None


class VideoComposer:
    """FFmpeg 视频合成器。"""

    def __init__(self, target_size: Tuple[int, int] = (1920, 1080)):
        self.ffmpeg_bin = get_ffmpeg_path()
        if not self.ffmpeg_bin:
            raise RuntimeError(
                "未找到 ffmpeg。三种解决方案：\n\n"
                "方案 A（推荐）：把 ffmpeg 加到系统 PATH\n"
                "  Windows: 把 ffmpeg.exe 所在目录加入系统环境变量 Path\n"
                "  Mac:     brew install ffmpeg\n"
                "  Linux:   sudo apt install ffmpeg\n\n"
                "方案 B：在 .env 文件中设置 FFMPEG_PATH，例如：\n"
                "  FFMPEG_PATH=D:\\agent\\ffmpeg-8.1.1\\bin\\ffmpeg.exe\n\n"
                "方案 C（Windows）：把 ffmpeg.exe 放到以下位置之一：\n"
                "  C:\\ffmpeg\\bin\\ffmpeg.exe\n"
                "  D:\\ffmpeg\\bin\\ffmpeg.exe"
            )
        logger.info(f"使用 ffmpeg: {self.ffmpeg_bin}")
        self.target_size = target_size

    def _run_ffmpeg(self, args: list[str], description: str = ""):
        """执行 ffmpeg 命令。"""
        cmd = [self.ffmpeg_bin, "-y", "-loglevel", "warning"] + args
        logger.info(f"FFmpeg: {description}")
        logger.debug(f"命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg 失败：\n{result.stderr}")
            raise RuntimeError(f"FFmpeg 错误：{result.stderr}")
        return result

    def compose(
        self,
        image_paths: list[Path],
        audio_paths: list[Path],
        scene_durations: list[float],
        output_path: Path,
        srt_path: Optional[Path] = None,
        bgm_path: Optional[Path] = None,
        bgm_volume: float = 0.15,
    ) -> Path:
        """
        合成视频。
        
        Args:
            image_paths: 每个分镜对应一张图
            audio_paths: 每个分镜的口播音频
            scene_durations: 每个分镜的设计时长（实际时长以音频为准）
            output_path: 输出 mp4 路径
            srt_path: 字幕文件（可选）
            bgm_path: 背景音乐（可选）
            bgm_volume: 背景音乐音量（0-1）
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 临时目录
        tmp_dir = output_path.parent / f".tmp_{output_path.stem}"
        tmp_dir.mkdir(exist_ok=True)

        try:
            # === 步骤 1：每个分镜单独生成一段视频（图+音频）===
            scene_videos = []
            for i, (img, audio, duration) in enumerate(
                zip(image_paths, audio_paths, scene_durations)
            ):
                scene_video = tmp_dir / f"scene_{i:03d}.mp4"
                # -loop 1 把单张图当成无限循环；-t 指定时长（用音频实际时长）
                self._run_ffmpeg(
                    [
                        "-loop", "1",
                        "-i", str(img),
                        "-i", str(audio),
                        "-c:v", "libx264",
                        "-tune", "stillimage",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-vf", f"scale={self.target_size[0]}:{self.target_size[1]}:force_original_aspect_ratio=decrease,"
                                f"pad={self.target_size[0]}:{self.target_size[1]}:(ow-iw)/2:(oh-ih)/2",
                        "-shortest",  # 跟随最短的输入流
                        str(scene_video),
                    ],
                    description=f"渲染分镜 {i + 1}/{len(image_paths)}",
                )
                scene_videos.append(scene_video)

            # === 步骤 2：把所有分镜串起来 ===
            concat_list = tmp_dir / "concat.txt"
            concat_list.write_text(
                "\n".join(f"file '{v.absolute()}'" for v in scene_videos),
                encoding="utf-8",
            )

            merged_video = tmp_dir / "merged.mp4"
            self._run_ffmpeg(
                [
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list),
                    "-c", "copy",
                    str(merged_video),
                ],
                description="拼接所有分镜",
            )

            # === 步骤 3：（可选）加背景音乐 ===
            if bgm_path and Path(bgm_path).exists():
                with_bgm = tmp_dir / "with_bgm.mp4"
                self._run_ffmpeg(
                    [
                        "-i", str(merged_video),
                        "-stream_loop", "-1",  # BGM 循环播放
                        "-i", str(bgm_path),
                        "-filter_complex",
                        f"[1:a]volume={bgm_volume}[bgm];"
                        f"[0:a][bgm]amix=inputs=2:duration=first[a]",
                        "-map", "0:v",
                        "-map", "[a]",
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        str(with_bgm),
                    ],
                    description="叠加背景音乐",
                )
                merged_video = with_bgm

            # === 步骤 4：（可选）烧录字幕 ===
            if srt_path and Path(srt_path).exists():
                # FFmpeg 字幕滤镜需要字符串转义
                srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")
                self._run_ffmpeg(
                    [
                        "-i", str(merged_video),
                        "-vf",
                        f"subtitles='{srt_escaped}':force_style='FontName=Microsoft YaHei,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=2'",
                        "-c:a", "copy",
                        str(output_path),
                    ],
                    description="烧录字幕",
                )
            else:
                shutil.move(merged_video, output_path)

            logger.info(f"✅ 视频合成完成：{output_path}")
            return output_path

        finally:
            # 清理临时文件
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
