"""
TTS 语音合成

使用 Edge-TTS（微软 Azure 神经语音的免费包装）
- 完全免费、无需 API Key
- 中文音色质量接近真人
- 支持 SSML 控制语速/语调

为什么选 Edge-TTS：
- 开源（任何人 fork 后能用，不绑定商业 API）
- 免费（不增加成本）
- 中文效果好（XiaoxiaoNeural / YunxiNeural 等音色）

未来扩展：
- FishAudio（音色克隆）
- OpenAI TTS
- ElevenLabs
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# 推荐的中文音色（按场景）
RECOMMENDED_VOICES = {
    "default": "zh-CN-XiaoxiaoNeural",        # 通用，亲切
    "professional": "zh-CN-YunxiNeural",       # 男声，专业
    "warm": "zh-CN-XiaoyiNeural",              # 女声，温暖
    "energetic": "zh-CN-YunjianNeural",        # 男声，活力
    "documentary": "zh-CN-YunyangNeural",      # 旁白感
}


class EdgeTTS:
    """基于 Edge-TTS 的语音合成器。"""

    def __init__(
        self,
        voice: str = "zh-CN-XiaoxiaoNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def _async_synthesize(self, text: str, output_path: Path):
        """异步合成（edge-tts 是异步库）。"""
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "缺少 edge-tts，请安装：pip install edge-tts"
            )
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
        )
        await communicate.save(str(output_path))

    def synthesize(self, text: str, output_path: Path) -> Path:
        """合成语音到文件。"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 同步包装异步调用
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("事件循环已关闭")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(self._async_synthesize(text, output_path))
        logger.info(f"TTS 合成完成：{output_path}")
        return output_path

    def synthesize_scenes(
        self,
        scenes: list,                # list[Scene]
        output_dir: Path,
    ) -> list[Path]:
        """为每个分镜生成对应的语音文件。"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        audio_paths = []
        for scene in scenes:
            if not scene.narration:
                logger.warning(f"分镜 {scene.index} 无口播文本，跳过")
                continue
            audio_path = output_dir / f"scene_{scene.index:03d}.mp3"
            self.synthesize(scene.narration, audio_path)
            audio_paths.append(audio_path)
        return audio_paths

    @staticmethod
    async def list_voices(language: str = "zh-CN") -> list[dict]:
        """列出某种语言的所有可用音色。"""
        try:
            import edge_tts
        except ImportError:
            raise ImportError("pip install edge-tts")
        
        voices = await edge_tts.list_voices()
        return [v for v in voices if v.get("Locale", "").startswith(language)]
