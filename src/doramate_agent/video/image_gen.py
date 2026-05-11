"""
图像生成

由于 DeepSeek 暂未公开图像生成 API，且我们要保证 fork 后任何人都能跑：
- 主要策略：使用占位图 + 提示用户用 SD/Midjourney/DALL-E 替换
- 占位图基于 Pillow 生成（纯 Python，零外部依赖）
- 配色用 project.yaml 里的 brand color（保持品牌一致性）

未来扩展：
- StableDiffusion 本地（占位策略保留作为 fallback）
- DALL-E API
- 阿里通义万相
- 智谱 CogView
"""
from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from typing import Optional, Tuple

from ..utils import get_project_config

logger = logging.getLogger(__name__)


# 默认尺寸（兼顾 16:9 和 9:16）
DEFAULT_LANDSCAPE = (1920, 1080)   # B 站
DEFAULT_PORTRAIT = (1080, 1920)    # 小红书视频


class PlaceholderImageGenerator:
    """
    占位图生成器
    
    生成一张干净的、品牌色的图片，上面带场景描述。
    虽然不是真正的 AI 生图，但能让整个视频流水线先跑通。
    用户可以替换为真实 AI 生图后重跑 composite。
    """

    def __init__(
        self,
        primary_color: str = None,
        secondary_color: str = None,
        font_path: Optional[str] = None,
    ):
        cfg = get_project_config()
        self.primary_color = primary_color or cfg.get("project.brand.primary_color", "#FF6B35")
        self.secondary_color = secondary_color or cfg.get("project.brand.secondary_color", "#2E5C8A")
        self.font_path = font_path

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        h = hex_color.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    def generate(
        self,
        text: str,
        output_path: Path,
        size: Tuple[int, int] = DEFAULT_LANDSCAPE,
        scene_index: int = 0,
    ) -> Path:
        """生成一张占位图。"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            raise ImportError("pip install Pillow")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建画布（用 secondary_color 做背景，更柔和）
        bg_color = self._hex_to_rgb(self.secondary_color)
        img = Image.new("RGB", size, bg_color)
        draw = ImageDraw.Draw(img)

        # 主色装饰条
        primary_rgb = self._hex_to_rgb(self.primary_color)
        bar_height = size[1] // 20
        draw.rectangle([0, 0, size[0], bar_height], fill=primary_rgb)
        draw.rectangle([0, size[1] - bar_height, size[0], size[1]], fill=primary_rgb)

        # 加载字体
        font_size = size[1] // 20
        try:
            if self.font_path and Path(self.font_path).exists():
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                # 尝试系统中文字体
                for fp in [
                    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                    "/System/Library/Fonts/STHeiti Medium.ttc",
                    "C:\\Windows\\Fonts\\msyh.ttc",
                ]:
                    if Path(fp).exists():
                        font = ImageFont.truetype(fp, font_size)
                        break
                else:
                    font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # 居中绘制场景索引（大字）
        scene_label = f"Scene {scene_index}"
        try:
            bbox = draw.textbbox((0, 0), scene_label, font=font)
            label_w = bbox[2] - bbox[0]
            label_h = bbox[3] - bbox[1]
        except Exception:
            label_w, label_h = font_size * 6, font_size

        draw.text(
            ((size[0] - label_w) // 2, size[1] // 4),
            scene_label,
            fill=primary_rgb,
            font=font,
        )

        # 绘制描述文本（小字，自动换行）
        try:
            small_font = ImageFont.truetype(font.path, font_size // 2) if hasattr(font, "path") else font
        except Exception:
            small_font = font

        wrapped = textwrap.wrap(text, width=size[0] // (font_size // 2 + 2))[:5]
        y = size[1] // 2
        for line in wrapped:
            try:
                bbox = draw.textbbox((0, 0), line, font=small_font)
                line_w = bbox[2] - bbox[0]
            except Exception:
                line_w = len(line) * (font_size // 2)
            draw.text(
                ((size[0] - line_w) // 2, y),
                line,
                fill=(255, 255, 255),
                font=small_font,
            )
            y += font_size // 2 + 10

        # 底部水印（项目名）
        cfg = get_project_config()
        project_name = cfg.get("project.name", "")
        if project_name:
            draw.text(
                (size[0] - len(project_name) * 20 - 30, size[1] - bar_height - 30),
                project_name,
                fill=(255, 255, 255),
                font=small_font,
            )

        img.save(output_path)
        logger.info(f"占位图已生成：{output_path}")
        return output_path

    def generate_for_scenes(
        self,
        scenes: list,            # list[Scene]
        output_dir: Path,
        size: Tuple[int, int] = DEFAULT_LANDSCAPE,
    ) -> list[Path]:
        """为所有分镜生成占位图。"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        paths = []
        for scene in scenes:
            path = output_dir / f"scene_{scene.index:03d}.png"
            self.generate(
                text=scene.visual_description,
                output_path=path,
                size=size,
                scene_index=scene.index,
            )
            paths.append(path)
        return paths
