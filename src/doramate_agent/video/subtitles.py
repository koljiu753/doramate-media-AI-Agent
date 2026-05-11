"""
字幕生成

基于 narration 文本 + TTS 音频时长，生成 SRT 字幕文件。
不需要语音识别（Whisper），因为我们有原文本，只需对齐时间戳。

如果未来要做"已有视频的字幕识别"，可加入 whisper.py 作为可选模块。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_audio_duration(audio_path: Path) -> float:
    """获取音频时长（秒）。"""
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(audio_path))
        return audio.info.length
    except Exception:
        # 备选：用 ffprobe
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True,
        )
        return float(result.stdout.strip())


def format_srt_timestamp(seconds: float) -> str:
    """秒数 → SRT 时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds * 1000) % 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def split_text_for_subtitles(text: str, max_chars: int = 20) -> list[str]:
    """
    将一段口播文本切分为多条字幕（避免一行字幕过长）。
    
    中文字幕规范：每条 15-20 字以内最佳。
    """
    # 优先按标点切
    import re
    segments = re.split(r"(?<=[。！？，；,;])", text)
    segments = [s.strip() for s in segments if s.strip()]
    
    # 把过长的段落继续切
    result = []
    for seg in segments:
        if len(seg) <= max_chars:
            result.append(seg)
        else:
            # 强制按字数切
            for i in range(0, len(seg), max_chars):
                result.append(seg[i : i + max_chars])
    return result


def generate_srt(
    scenes: list,            # list[Scene]
    audio_paths: list[Path], # 与 scenes 一一对应
    output_path: Path,
) -> Path:
    """
    生成 SRT 字幕文件。
    
    每个 scene 的口播会被切分成多条字幕，时长按比例分配。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    srt_lines = []
    counter = 1
    current_time = 0.0  # 累积时间（秒）

    for scene, audio_path in zip(scenes, audio_paths):
        if not scene.narration:
            current_time += scene.duration_seconds
            continue
        
        # 实际音频时长（不一定等于设计的 duration_seconds）
        actual_duration = get_audio_duration(audio_path)
        
        # 切分字幕段
        sub_lines = split_text_for_subtitles(scene.narration)
        if not sub_lines:
            current_time += actual_duration
            continue
        
        # 按字符数比例分配时长
        total_chars = sum(len(s) for s in sub_lines)
        for sub in sub_lines:
            ratio = len(sub) / total_chars if total_chars > 0 else 1 / len(sub_lines)
            sub_duration = actual_duration * ratio
            
            start = current_time
            end = current_time + sub_duration
            
            srt_lines.append(str(counter))
            srt_lines.append(
                f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}"
            )
            srt_lines.append(sub)
            srt_lines.append("")
            counter += 1
            current_time = end

    output_path.write_text("\n".join(srt_lines), encoding="utf-8")
    logger.info(f"字幕生成完成：{output_path}（共 {counter - 1} 条）")
    return output_path
