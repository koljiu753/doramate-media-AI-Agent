# 架构设计文档

## 设计目标

> **构建一个可持续运行的开源内容工厂，让任何开源项目都能用 1-2 人的资源做到 10 人的内容运营产出。**

---

## 核心原则（与 v0.1 的区别）

### 原则 1：配置驱动，零硬编码

**v0.1（错的）**：
```python
PROJECT_NAME = "DoraMate"  # 写死在代码里
SPONSOR_TAG = "Supported by Upstream Labs"  # 写死
```

**v0.2（对的）**：
```yaml
# config/project.yaml
project:
  name: "DoraMate"   # 别人 fork 改这里就行
sponsors:
  required_attribution:
    - combined: "源起之道支持｜Supported by Upstream Labs"
```

```python
# 代码里
from doramate_agent.utils import get_project_config
cfg = get_project_config()
print(cfg.get("project.name"))  # 动态读取
```

### 原则 2：插件化架构

**加新平台不改代码**：
```
plugins/platforms/
  ├── csdn.yaml        ← 内置
  ├── xiaohongshu.yaml ← 内置
  ├── zhihu.yaml       ← 内置
  ├── bilibili.yaml    ← 内置
  ├── wechat.yaml      ← 内置
  └── 你的新平台.yaml    ← 用户加
```

启动时自动扫描这个目录，加载所有 yaml。

**加新 LLM Provider 也不需要改主代码**：
```python
# src/doramate_agent/llm/your_provider.py
@LLMRegistry.register("your_provider")
class YourLLM(BaseLLM):
    def generate(self, prompt, **kw):
        ...
```

只要 import 这个文件，新 Provider 就自动注册了。

### 原则 3：Provider 抽象层

```
┌──────────────────────────┐
│   CreatorAgent           │   ← 业务逻辑
└────────┬─────────────────┘
         │ 用接口，不知道具体实现
         ▼
┌──────────────────────────┐
│   BaseLLM (abstract)     │   ← 统一接口
└────────┬─────────────────┘
         │ 多种实现
   ┌─────┴─────┬─────────┬──────────┐
   ▼           ▼         ▼          ▼
DeepSeek   OpenAI    Claude     Ollama
```

切换 LLM 只改配置，业务代码完全不变。

### 原则 4：标准开源项目卫生

v0.2 含：
- ✅ Apache 2.0 LICENSE
- ✅ README.md（中英双语）
- ✅ CONTRIBUTING.md
- ✅ pyproject.toml（标准 Python 打包）
- ✅ 单元测试（pytest）
- ✅ GitHub Actions CI
- ✅ .gitignore（防止 .env 泄露）

---

## 模块依赖关系

```
┌──────────────────────────────────────────────┐
│  cli.py（命令行入口）                          │
└───────┬──────────────┬──────────────┬─────────┘
        │              │              │
        ▼              ▼              ▼
   ┌────────┐    ┌──────────┐  ┌──────────┐
   │Creator │    │  Video   │  │  Doctor  │
   │ Agent  │    │  Agent   │  │  CLI     │
   └────┬───┘    └────┬─────┘  └──────────┘
        │             │
        ▼             ▼
   ┌──────────────────────────┐
   │     Platform Registry    │
   └──────────┬───────────────┘
              │
              ▼
       ┌──────────────┐
       │ LLM Registry │ ◄── 多 Provider 注册
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │   Config     │ ◄── project.yaml + agent.yaml
       │   System     │
       └──────────────┘
```

---

## 视频自动化流水线

```
[topic 输入]
     │
     ▼
[ScriptGenerator]
     │ → script.json (标题/分镜/口播文本/视觉描述)
     │
     ├─────────────┬─────────────┬─────────────┐
     ▼             ▼             ▼             ▼
[TTS]         [ImageGen]    [Subtitle]    [Thumbnail]
edge-tts      占位图/AI生图   SRT 时间轴    封面 prompt
     │             │             │
     └─────────────┴─────────────┘
                   │
                   ▼
            [Composer]
            FFmpeg 拼接
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   横屏 mp4              竖屏 mp4
   (B站 1920x1080)       (小红书 1080x1920)
```

**关键设计决策**：
- **TTS 用 Edge-TTS**：免费 + 中文质量好 + 无 API 依赖（开源友好）
- **图用占位图先跑通**：避免 Phase 5 MVP 因图像生成 API 复杂而拖延；后续 Phase 6 替换
- **字幕基于原文本而非 ASR**：因为我们有 narration 原文，对齐更准
- **横竖屏一起出**：B站和小红书是不同的尺寸，FFmpeg 一次构建两次输出更高效

---

## 数据流（Phase 1：创作 Agent）

```
用户输入 topic
     │
     ▼
1. 加载 project.yaml + agent.yaml
2. 加载知识库 data/dora_knowledge.md
3. 选择平台（默认 5 个 / 用户指定）
     │
     ▼
对每个平台：
  4. 加载 prompts/platforms/{platform}.txt
  5. 注入项目身份变量（{project_name}, {project_github} 等）
  6. 注入主题 + 知识库 + user_hint
     │
     ▼
  7. 调 LLM 生成
  8. 保存到 output/content/{时间戳}_{slug}_{platform}.md
  9. 记录成本 + tokens
     │
     ▼
返回 CreatorRunResult（成功数、总成本、文件路径）
```

---

## 知识库注入（防胡说核心）

为什么要做：
- LLM 容易把 `pip install dora-rs` 写成 `pip install dora`
- LLM 可能编造 dora-rs 的特性
- LLM 可能把 DoraMate 描述错（说成"取代 dora"而不是"基于 dora"）

怎么做：
- `data/dora_knowledge.md` 是结构化的事实库
- 包含"不要这样说"的禁区
- 每次生成前作为 prompt context 塞进去
- 错了就来这里补，下次自动修正

---

## 扩展性场景

### 场景 1：dora 中文社区另一个项目想用

```bash
# 他们 fork 这个仓库
git clone https://github.com/DoraCN/agent-template.git
cd agent-template

# 改 5 行配置
vim config/project.yaml  # 改 name/github/website
vim data/dora_knowledge.md  # 替换为他们项目的知识

# 立刻能用
doramate-agent create --topic "..."
```

### 场景 2：完全无关的开源项目（比如某 Rust 库）

```bash
# 同样 fork
# 改 project.yaml（不只是 name，还有 keywords, parent_project 等）
# 替换 prompts/platforms/* 为他们领域的风格
# 用
```

### 场景 3：内部用，私有部署

```bash
# 用本地 Ollama 而不是 DeepSeek
# 在 src/doramate_agent/llm/ollama.py 加一个 Provider
# 改 config/agent.yaml: default_provider: "ollama"
```

---

## 后续路线（Phase 2-6）

| Phase | 内容 | 关键文件 |
|---|---|---|
| ✅ 1 | 创作 Agent | agents/creator.py |
| ⏳ 2 | 选题 Agent | agents/curator.py |
| ⏳ 3 | Streamlit UI | ui/streamlit_app.py |
| ⏳ 4 | 周报 Agent | agents/reporter.py |
| ✅ 5 MVP | 视频 Agent | agents/video.py + video/* |
| ⏳ 6 | AI 生图替换占位图 | video/image_gen.py 扩展 |

---

> 源起之道支持｜Supported by Upstream Labs
