from __future__ import annotations

import html
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from doramate_agent.agents import CreatorAgent, VideoAgent
from doramate_agent.utils import PROJECT_ROOT

logger = logging.getLogger(__name__)

DEFAULT_TOPIC = "dora-rs 新手从哪里开始：中文社区学习路线"
DEFAULT_HINT = (
    "面向第一次听说 dora-rs 的中文开发者。强调 DoraCN 中文社区学习路线："
    "先理解 dora-rs 是什么，再跑通 quick-start，再看核心概念、示例库、社区交流。"
    "不要夸大 DoraMate 功能。必须标注 源起之道支持｜Supported by Upstream Labs。"
)


def _page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --bg:#f8fafc; --brand:#2563eb; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif; color:var(--ink); background:var(--bg); }}
    main {{ max-width:1040px; margin:0 auto; padding:24px; }}
    header {{ padding:20px 24px; background:white; border-bottom:1px solid var(--line); }}
    h1 {{ margin:0; font-size:24px; }}
    h2 {{ margin-top:28px; font-size:18px; }}
    p, label {{ color:var(--muted); line-height:1.7; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
    .card {{ background:white; border:1px solid var(--line); border-radius:8px; padding:18px; margin:16px 0; }}
    input, textarea, select {{ width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid var(--line); border-radius:8px; font:inherit; background:white; }}
    textarea {{ min-height:110px; }}
    button {{ background:var(--brand); color:white; border:0; border-radius:8px; padding:10px 14px; font-weight:600; cursor:pointer; }}
    code, pre {{ font-family:"JetBrains Mono","Cascadia Code",monospace; }}
    pre {{ white-space:pre-wrap; background:#0f172a; color:#e5e7eb; padding:14px; border-radius:8px; overflow:auto; }}
    a {{ color:var(--brand); }}
    .muted {{ color:var(--muted); }}
    .ok {{ color:#047857; }}
    .err {{ color:#b91c1c; }}
    @media (max-width: 780px) {{ .grid {{ grid-template-columns:1fr; }} main {{ padding:16px; }} }}
  </style>
</head>
<body>
  <header><h1>DoraMate Media Agent</h1><p class="muted">手机/电脑浏览器操作台。生成时请保持页面打开。</p></header>
  <main>{body}</main>
</body>
</html>""".encode("utf-8")


def _home(message: str = "") -> bytes:
    latest = _latest_outputs_html()
    msg = f'<div class="card">{message}</div>' if message else ""
    body = f"""
{msg}
<div class="grid">
  <section class="card">
    <h2>生成视频</h2>
    <form method="post" action="/video">
      <label>视频主题</label>
      <input name="topic" value="{html.escape(DEFAULT_TOPIC)}">
      <label>额外提示</label>
      <textarea name="hint">{html.escape(DEFAULT_HINT)}</textarea>
      <label>目标时长（秒）</label>
      <input name="duration" type="number" value="90" min="45" max="240">
      <label>视觉风格预设</label>
      <select name="style_preset">
        <option value="">使用配置默认风格</option>
        <option value="editorial">editorial 成熟社区编辑插画</option>
        <option value="isometric">isometric 低饱和系统地图</option>
        <option value="screenflow">screenflow 文档/界面流程感</option>
        <option value="bold_cover">bold_cover 强封面风格</option>
      </select>
      <label>额外审美偏好（可选）</label>
      <input name="style_hint" placeholder="例如 更像成熟开源社区官网插画，不要儿童教育感">
      <label>音色预设</label>
      <select name="voice_preset">
        <option value="">使用配置默认音色</option>
        <option value="default">default 女声通用</option>
        <option value="professional">professional 男声专业</option>
        <option value="warm">warm 女声温暖</option>
        <option value="energetic">energetic 男声活力</option>
        <option value="documentary">documentary 男声旁白</option>
      </select>
      <label>自定义 Edge-TTS 音色 ID（可选，优先级高于预设）</label>
      <input name="voice" placeholder="例如 zh-CN-YunxiNeural">
      <label>语速（可选）</label>
      <input name="rate" placeholder="例如 +8% 或 -5%">
      <label>音调（可选）</label>
      <input name="pitch" placeholder="例如 +0Hz">
      <label>背景音乐路径（可选）</label>
      <input name="bgm" placeholder="D:\\\\music\\\\bgm.mp3">
      <p><label><input type="checkbox" name="no_landscape"> 跳过横屏版</label></p>
      <p><label><input type="checkbox" name="no_portrait"> 跳过竖屏版</label></p>
      <button type="submit">开始生成视频</button>
    </form>
  </section>

  <section class="card">
    <h2>生成平台文案</h2>
    <form method="post" action="/content">
      <label>内容主题</label>
      <input name="topic" value="{html.escape(DEFAULT_TOPIC)}">
      <label>额外提示</label>
      <textarea name="hint">{html.escape(DEFAULT_HINT)}</textarea>
      <label>平台（逗号分隔）</label>
      <input name="platforms" value="bilibili,xiaohongshu,wechat">
      <button type="submit">生成文案</button>
    </form>
  </section>
</div>

<section class="card">
  <h2>替换 AI 图片后重新合成</h2>
  <p>先用外部 AI 生图工具生成分镜图片，覆盖工作目录里的 <code>images_landscape</code> / <code>images_portrait</code>，再重新合成。</p>
  <form method="post" action="/recompose">
    <label>视频工作目录</label>
    <input name="work_dir" placeholder="D:\\agent\\doramate_agent_v2\\output\\videos\\20260602_xxx">
    <label>背景音乐路径（可选）</label>
    <input name="bgm">
    <p><label><input type="checkbox" name="no_landscape"> 跳过横屏版</label></p>
    <p><label><input type="checkbox" name="no_portrait"> 跳过竖屏版</label></p>
    <button type="submit">重新合成</button>
  </form>
</section>

<section class="card">
  <h2>最近产物</h2>
  {latest}
</section>
"""
    return _page("DoraMate Media Agent", body)


def _latest_outputs_html() -> str:
    root = PROJECT_ROOT / "output" / "videos"
    if not root.exists():
        return "<p class='muted'>暂无视频产物。</p>"
    dirs = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)[:8]
    if not dirs:
        return "<p class='muted'>暂无视频产物。</p>"
    rows = []
    for d in dirs:
        metadata = d / "metadata.json"
        title = d.name
        if metadata.exists():
            try:
                title = json.loads(metadata.read_text(encoding="utf-8")).get("title") or title
            except Exception:
                pass
        rows.append(f"<li><strong>{html.escape(title)}</strong><br><code>{html.escape(str(d))}</code></li>")
    return "<ul>" + "\n".join(rows) + "</ul>"


def _read_post(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    length = int(handler.headers.get("Content-Length", "0"))
    data = handler.rfile.read(length).decode("utf-8")
    parsed = parse_qs(data)
    return {k: v[-1] if v else "" for k, v in parsed.items()}


def _render_video_result(outputs: dict) -> str:
    lines = ["<h2 class='ok'>视频生成完成</h2>"]
    lines.append(f"<p>工作目录：<code>{html.escape(outputs.get('work_dir', ''))}</code></p>")
    if outputs.get("title"):
        lines.append(f"<p><strong>{html.escape(outputs['title'])}</strong></p>")
    if outputs.get("voice"):
        lines.append(
            "<p>音色：<code>{voice}</code> 语速：<code>{rate}</code> 音调：<code>{pitch}</code></p>".format(
                voice=html.escape(outputs.get("voice", "")),
                rate=html.escape(outputs.get("voice_rate", "")),
                pitch=html.escape(outputs.get("voice_pitch", "")),
            )
        )
    if outputs.get("style_preset"):
        lines.append(f"<p>视觉风格：<code>{html.escape(outputs.get('style_preset', ''))}</code></p>")
    for key, label in [("video_landscape", "B站横屏版"), ("video_portrait", "小红书/视频号竖屏版")]:
        if outputs.get(key):
            lines.append(f"<p>{label}：<code>{html.escape(outputs[key])}</code></p>")
    if outputs.get("script_json"):
        lines.append(f"<p>分镜脚本：<code>{html.escape(outputs['script_json'])}</code></p>")
    for key, label in [
        ("script_markdown", "可读脚本"),
        ("image_prompt_sheet", "AI 生图提示词清单"),
        ("style_reference", "风格母版生成说明"),
        ("style_guide", "视频视觉风格锁"),
        ("review_checklist", "发布前审核清单"),
        ("next_steps", "下一步操作说明"),
    ]:
        if outputs.get(key):
            lines.append(f"<p>{label}：<code>{html.escape(outputs[key])}</code></p>")
    return "\n".join(lines)


class AgentRequestHandler(BaseHTTPRequestHandler):
    def _send(self, content: bytes, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):  # noqa: N802
        self._send(_home())

    def do_POST(self):  # noqa: N802
        try:
            data = _read_post(self)
            if self.path == "/video":
                outputs = VideoAgent().run(
                    topic=data.get("topic", DEFAULT_TOPIC),
                    user_hint=data.get("hint", ""),
                    target_duration=int(data.get("duration", "90") or "90"),
                    bgm_path=Path(data["bgm"]) if data.get("bgm") else None,
                    skip_landscape="no_landscape" in data,
                    skip_portrait="no_portrait" in data,
                    voice=data.get("voice") or None,
                    voice_preset=data.get("voice_preset") or None,
                    rate=data.get("rate") or None,
                    pitch=data.get("pitch") or None,
                    style_preset=data.get("style_preset") or None,
                    style_hint=data.get("style_hint") or None,
                )
                self._send(_home(_render_video_result(outputs)))
                return

            if self.path == "/content":
                platforms = [p.strip() for p in data.get("platforms", "").split(",") if p.strip()]
                result = CreatorAgent().run(
                    topic=data.get("topic", DEFAULT_TOPIC),
                    platforms=platforms or None,
                    user_hint=data.get("hint", ""),
                )
                parts = [f"<h2 class='ok'>文案生成完成：{result.success_count}/{len(result.results)}</h2>"]
                for item in result.results:
                    if item.success:
                        text = item.file_path.read_text(encoding="utf-8")
                        parts.append(f"<h3>{html.escape(item.platform_name)}</h3><p><code>{html.escape(str(item.file_path))}</code></p><pre>{html.escape(text)}</pre>")
                    else:
                        parts.append(f"<p class='err'>{html.escape(item.platform_name)}：{html.escape(item.error or '')}</p>")
                self._send(_home("\n".join(parts)))
                return

            if self.path == "/recompose":
                outputs = VideoAgent().recompose(
                    work_dir=Path(data.get("work_dir", "")),
                    bgm_path=Path(data["bgm"]) if data.get("bgm") else None,
                    skip_landscape="no_landscape" in data,
                    skip_portrait="no_portrait" in data,
                )
                self._send(_home(_render_video_result(outputs)))
                return

            self._send(_home("<p class='err'>未知请求。</p>"), status=404)
        except Exception as exc:
            logger.exception("Web UI request failed")
            self._send(_home(f"<h2 class='err'>执行失败</h2><pre>{html.escape(str(exc))}</pre>"), status=500)


def run_server(host: str = "127.0.0.1", port: int = 8501) -> int:
    server = ThreadingHTTPServer((host, port), AgentRequestHandler)
    print("\n" + "=" * 60)
    print("🌐 DoraMate Agent Web UI")
    print("=" * 60)
    print(f"电脑访问：http://127.0.0.1:{port}")
    if host == "0.0.0.0":
        print(f"手机访问：请使用电脑局域网 IP + 端口，例如 http://192.168.x.x:{port}")
    print("按 Ctrl+C 退出。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出 Web UI。")
    finally:
        server.server_close()
    return 0
