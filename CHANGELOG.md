# Changelog

所有重要变更都会记录在这里。本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [0.2.1] - 2026-06-02

### Added
- 新增 `doramate-agent web` 命令,提供 Streamlit 浏览器页面,支持电脑/手机输入主题生成视频或多平台文案。
- 新增 `doramate-agent recompose` 命令,支持外部 AI 生图工具替换分镜图片后重新合成横屏/竖屏视频。
- 新增 `docs/WEB_UI.md`,记录手机访问、Web UI 和 AI 生图替换流程。
- 视频生成时新增生产包: `video_script.md`、`ai_image_prompts.md`、`review_checklist.md`、`NEXT_STEPS.md`,便于使用外部 AI 生图会员账号完成素材替换和发布审核。
- 新增 `STYLE_GUIDE.md` 视觉风格锁,让同一条视频所有分镜图片使用统一色彩、构图、材质和禁用项。
- 新增 TTS 音色选择: `doramate-agent voices`、`video --voice-preset/--voice/--rate/--pitch`,Web UI 同步支持音色预设。

### Changed
- 升级 5 个平台 prompt 到 v2.2,强化输出协议,避免"好的/收到/以下是"等 meta 开场白。
- 修正小红书、知乎、B 站等平台的作者身份约束,保持冯小婷的产品/UX 设计师视角。
- 更新 Dora 知识库,明确 DoraMate 当前处于开发中,避免编造网页版编辑器、节点市场、一键部署、监控界面、硬件 demo 等未实现功能。
- 增加 v2.2.1 热修约束:禁止虚构采访/用户反馈/团队合影,禁止把 dora-rs 的 Rust 内核写成 DoraMate 团队成果,禁止编造具体性能数字。

## [0.2.0] - 2026-05-09

### 重大重构 - 从冲刺工具升级为开源框架

#### Added
- 🎬 **视频自动化模块（Phase 5 MVP）**
  - 脚本+分镜生成（基于 LLM）
  - Edge-TTS 中文配音（免费，微软神经语音）
  - SRT 字幕自动生成（基于 narration + 音频时长）
  - FFmpeg 视频合成（横屏 1920x1080 + 竖屏 1080x1920）
  - 占位图生成器（流水线先跑通，后续可替换为真实 AI 生图）
- 🔌 **平台插件系统**：加新平台只需 yaml + prompt 模板，无需改代码
- 🤖 **LLM 抽象层**：支持 DeepSeek / OpenAI / Claude（Ollama 接口预留）
- 📋 **配置驱动架构**：`config/project.yaml` 一处改配置
- 🩺 **健康检查命令**：`doramate-agent doctor`
- 📦 **标准 Python 打包**：pyproject.toml + 可 `pip install -e .`
- ✅ **单元测试**：pytest + GitHub Actions CI
- 📜 **开源项目卫生**：LICENSE / CONTRIBUTING / CODE_OF_CONDUCT
- 📖 **文档**：架构设计、贡献指南、上手手册

#### Changed
- 重构所有硬编码的"DoraMate"/"冯小婷"为配置项
- 5 个平台 prompt 模板使用变量替换（{project_name} 等）

#### Removed
- v0.1 的单文件脚本结构（迁移到 src/ 包结构）

---

## [0.1.0] - 2026-05-09

### Added - MVP

- ✨ 创作 Agent（5 平台一稿多发）
- 🧠 Dora 知识库（防止 AI 胡说）
- 🔗 UTM 链接生成器
- 🚀 quickstart.sh / quickstart.bat 一键启动

---

## 路线图（未发布）

### [0.3.0]（计划）- Phase 4 周报 Agent
- CSDN/B 站数据采集
- KPI 自动统计
- 周报自动生成

### [0.4.0]（计划）- Phase 2 选题 Agent
- GitHub Trending 抓取
- arXiv 论文摘要
- 选题历史去重

### [0.5.0]（计划）- Phase 3 Streamlit Web UI

### [0.6.0]（计划）- Phase 6 真实 AI 生图
- 接入 DALL-E / SD / 通义万相 / 智谱 CogView
