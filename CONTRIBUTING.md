# Contributing to DoraMate Promo Agent

非常欢迎你为这个项目做贡献！下面是不同类型贡献的指南。

## 🌱 我能贡献什么？

### 🎯 简单（适合新手）

- 修正文档错别字、改进 README
- 报告 Bug：在 [Issues](../../issues) 提交，请提供：
  - 你跑的命令
  - 完整的错误信息
  - 你的环境（Python 版本、操作系统）

### 🔧 中等

- **新平台插件**：在 `plugins/platforms/` 加 YAML，在 `prompts/platforms/` 加模板
- **新 prompt 模板**：用更好的 prompt 提升某个平台的内容质量
- **改进知识库**：补充 `data/*.md` 的事实/错误纠正

### 🚀 高级

- **新 LLM Provider**：在 `src/doramate_agent/llm/` 加新模块（参考 deepseek.py）
- **新视频后端**：替换 PlaceholderImageGenerator 为真实 AI 生图
- **新 Agent**：实现 Phase 2-4 的 Agent

## 📋 贡献流程

```bash
# 1. Fork → clone 你的 fork
git clone https://github.com/你的用户名/DoraMate.git
cd DoraMate

# 2. 创建分支
git checkout -b feat/my-awesome-feature

# 3. 写代码 + 测试
pip install -e ".[dev]"
pytest

# 4. 提交（commit message 用约定式格式）
git commit -m "feat(platforms): 添加即刻平台插件"

# 5. 推送 + 提 PR
git push origin feat/my-awesome-feature
```

## 🎨 代码规范

- Python 3.10+，使用类型提示
- 用 `ruff` 格式化：`ruff format src/`
- 函数/类要写 docstring（中英文均可）
- 提交前跑测试：`pytest`

## 🌐 加新平台插件（最常见的贡献）

1. 创建 `plugins/platforms/jike.yaml`（参考 `csdn.yaml`）
2. 创建 `prompts/platforms/jike.txt`
3. 测试：
   ```bash
   doramate-agent create --topic "测试" --platforms jike
   ```
4. 在 PR 描述里附上一个生成示例

## 🤝 行为准则

请遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。简单说：友善、尊重、不歧视。

## 💬 有疑问？

- 在 [Discussions](../../discussions) 提问
- 加微信群（见项目主页）

---

> 源起之道支持｜Supported by Upstream Labs
