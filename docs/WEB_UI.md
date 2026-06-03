# DoraMate Agent Web UI

这个页面用于在电脑或手机浏览器里操作 Agent,不需要记命令行参数。

## 启动

电脑本机使用:

```bash
doramate-agent web
```

手机访问同一台电脑:

```bash
doramate-agent web --host 0.0.0.0 --port 8501
```

然后在手机浏览器打开:

```text
http://你的电脑局域网IP:8501
```

这个 Web UI 使用 Python 标准库内置服务,不需要额外安装 Streamlit。

## 当前能力

- 输入主题和提示词,生成横屏/竖屏视频初版
- 输入主题,生成 CSDN/小红书/知乎/B站/公众号文案
- 查看最近产物
- 用外部 AI 生图工具替换分镜图片后,一键重新合成视频
- 每次视频生成都会附带 `video_script.md`、`ai_image_prompts.md`、`review_checklist.md` 和 `NEXT_STEPS.md`

## AI 生图工作流

当前默认仍会生成品牌占位图,保证全流程稳定跑通。

如果你有即梦、可灵、Midjourney、DALL-E 等账号:

1. 在 Web UI 生成视频初版
2. 打开工作目录里的 `ai_image_prompts.md`
3. 复制每个 Scene 的横屏/竖屏提示词
4. 用 AI 生图工具生成对应图片
5. 覆盖:
   - `images_landscape/scene_001.png`
   - `images_portrait/scene_001.png`
6. 回到 Web UI 的“替换图片后重合成”页,重新合成成片

后续如果接入有稳定 API 的图像/视频生成服务,可以把第 3-5 步改成自动化。
