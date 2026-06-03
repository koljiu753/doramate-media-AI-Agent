# DoraMate Promo Agent

> 为开源社区设计的 AI 内容生产 Agent · 一稿多发 + 全AI视频生成

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Status](https://img.shields.io/badge/Status-Phase%201%20%2B%205%20MVP-orange.svg)]()

**English** | [简体中文](README.zh.md)

---

## What is this?

DoraMate Promo Agent 是为 **DoraMate** 项目（基于 [dora-rs](https://dora-rs.ai) 的低代码具身智能开发平台）打造的内容生产 Agent，**同时也是一个可被任何开源项目复用的通用工具**。

它解决一个具体问题：**开源项目的 1-2 个核心维护者，没有时间也没有精力做内容运营，但内容运营又是社区增长的关键。**

### 它能做什么

| 能力 | 状态 | 说明 |
|---|---|---|
| 🎯 一稿多发 | ✅ Phase 1 | 输入主题，自动生成 CSDN/小红书/知乎/B站/公众号 5 平台适配文案 |
| 🎬 全AI视频生成 | ✅ Phase 5 MVP | 主题 → 脚本 → TTS 配音 → 图 → 字幕 → 成片（横屏+竖屏） |
| 🌐 浏览器操作台 | ✅ Phase 3 MVP | `doramate-agent web`，电脑/手机输入主题生成视频与平台文案 |
| 🧾 视频生产包 | ✅ | 自动输出可读脚本、AI 生图提示词清单、重合成说明和发布前审核清单 |
| 🎨 视觉风格锁 | ✅ | 每条视频自动生成 `STYLE_GUIDE.md`，支持多套风格预设，统一分镜生图风格 |
| 🎙️ 音色选择 | ✅ | 支持 `--voice-preset` / `--voice` / `--rate` 切换 Edge-TTS 音色 |
| 📊 选题推荐 | ⏳ Phase 2 | 抓取 GitHub Trending / arXiv / 热搜，每天推送选题 |
| 📈 周报 Agent | ⏳ Phase 4 | 自动统计各平台数据，生成 KPI 报告 |
| 🔗 UTM 链接 | ✅ | 流量漏斗追踪 |
| 🧠 知识库防胡说 | ✅ | 内置项目专属知识库 |

### 为什么是开源的

这个工具最初是为 DoraMate 登顶营冲刺写的，但我们发现：

> 大量开源项目（不只是 dora-rs 生态）都面临同样的问题——技术好、文档全，但**没有内容运营产能**。

所以我们把它**做成可 fork 的通用工具**：换一个项目，只需要改 `config/project.yaml` 的 5 行配置 + `data/knowledge.md` 的项目知识库。

---

## Quick Start

### 1. 安装

```bash
git clone https://github.com/DoraCN/DoraMate.git
cd DoraMate/agent  # 或你 clone 后的 agent 目录
pip install -e .
# 或：pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（推荐，国内直连）
```

申请 DeepSeek Key：https://platform.deepseek.com（10 元起步，按量计费）

### 3. 健康检查

```bash
doramate-agent doctor
```

输出应该看到所有 ✓。

### 4. 用起来

```bash
# 生成 5 平台内容
doramate-agent create --topic "DoraMate 拖拽节点教程"

# 生成视频（B站横屏 + 小红书竖屏）
doramate-agent video --topic "5 分钟看懂 dora-rs"

# 换音色：推荐先用 voices 看预设
doramate-agent voices
doramate-agent video --topic "5 分钟看懂 dora-rs" --voice-preset professional --rate +6%

# 换视觉风格：先看 styles，再指定 style-preset
doramate-agent styles
doramate-agent video --topic "dora-rs 新手从哪里开始：中文社区学习路线" --duration 90 --style-preset editorial --style-hint "更像成熟开源社区官网插画，不要儿童教育感"

# 生成后会得到:
# - video_script.md          可读分镜脚本
# - ai_image_prompts.md      横屏/竖屏 AI 生图提示词清单
# - STYLE_GUIDE.md           统一视觉风格锁
# - review_checklist.md      发布前审核清单
# - NEXT_STEPS.md            替换图片与重合成步骤

# 打开浏览器页面（电脑）
doramate-agent web

# 手机访问同一台电脑（同一 Wi-Fi 下）
doramate-agent web --host 0.0.0.0 --port 8501

# 只生成小红书 + B站
doramate-agent create --topic "..." --platforms xiaohongshu,bilibili

# 视频+背景音乐
doramate-agent video --topic "..." --bgm assets/music/upbeat.mp3

# 用外部 AI 生图工具替换分镜图片后重新合成视频
doramate-agent recompose --work-dir output/videos/你的工作目录
```

---

## Use this for your own project

想用这套工具运营你自己的开源项目？只需 4 步：

1. **Fork 这个仓库**

2. **改 `config/project.yaml`**：
   ```yaml
   project:
     name: "你的项目名"
     github: "https://github.com/你的组织/你的项目"
     website: "https://你的项目官网"
     # ...
   ```

3. **改 `data/dora_knowledge.md`**：把内容换成你项目的知识库（核心概念、技术细节、常见误解等）

4. **可选：改 `prompts/platforms/*.txt`**：针对你的领域调整 prompt 风格

完成。Agent 立刻可以为你的项目工作。

---

## 架构

```
你（开源项目维护者）
        ↓
   doramate-agent CLI
        ↓
┌────────────────────────────────────┐
│  CreatorAgent  │  VideoAgent  │ ... │  ← Agents 层
├────────────────────────────────────┤
│   Platform Plugins (yaml)          │  ← 加新平台：写一个 yaml
├────────────────────────────────────┤
│   LLM Providers (deepseek/openai)  │  ← 加新 LLM：写一个 class
├────────────────────────────────────┤
│   Project Identity (yaml)          │  ← Fork 时只改这里
└────────────────────────────────────┘
```

详细设计：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 路线图

### ✅ Phase 1：内容创作 Agent（已完成）
- 5 平台一稿多发
- Dora 知识库
- UTM 链接生成

### ✅ Phase 5 MVP：视频自动化（已完成基础）
- 脚本+分镜生成
- Edge-TTS 免费配音
- SRT 字幕
- FFmpeg 横屏+竖屏合成

### ⏳ Phase 2：选题 Agent
- GitHub Trending 抓取
- arXiv 论文摘要
- 历史选题去重

### ✅ Phase 3 MVP：Streamlit Web UI
- 浏览器操作（无需命令行）
- 电脑/手机输入主题生成视频或平台文案
- 替换外部 AI 生图素材后重新合成视频

使用说明：[docs/WEB_UI.md](docs/WEB_UI.md)

### ⏳ Phase 4：数据回流 + 周报
- CSDN/B站 API 数据采集
- KPI 自动统计
- 周报自动生成

### ⏳ Phase 6：视频 V2
- 真实 AI 生图（替换占位图）
- 转场动画
- 数字人形象

---

## Contributing

我们欢迎以下贡献：
- 新平台插件（即刻、Twitter、Mastodon...）
- 新 LLM Provider（通义千问、智谱、Ollama...）
- 新语言支持（英文、日文 prompt 模板）
- Bug 修复、文档改进

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## License

Apache 2.0（与 dora-rs 一致）

---

## 致谢

- [dora-rs](https://github.com/dora-rs/dora) - 上游机器人框架
- [Edge-TTS](https://github.com/rany2/edge-tts) - 免费的中文 TTS
- [DeepSeek](https://platform.deepseek.com) - 国产高性价比 LLM
- 项目导师 [李扬](https://echoli.cn)
- 核心贡献者：冯小婷、夏豪

---

> 源起之道支持｜Supported by Upstream Labs
