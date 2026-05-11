# Dora 知识库（Agent 内置参考）

> 这个文件是创作 Agent 的"事实校验源"。每次生成内容前，Agent 会把这里的关键信息塞进 Prompt，避免胡说。
> 维护原则：发现 Agent 写错了什么，就来这里补充正确版本。

---

## 1. Dora-rs 项目核心信息

### 是什么
DORA = **Dataflow-Oriented Robotic Architecture**（数据流导向的机器人架构）

是一个**基于 Rust 的开源机器人中间件**，目标是简化 AI 机器人应用的开发。它把机器人应用建模为**有向图（pipeline）**，由可组合的节点（node）通过类型化的输入/输出连接而成。

### 关键技术特点（千万别写错）
- **多语言节点**：原生支持 Rust、Python、C、C++（不是 wrapper，是 native API），可在一个 dataflow 里混用
- **声明式 YAML**：用 YAML 定义 dataflow，节点之间通过 typed inputs/outputs 连接
- **低延迟**：同机部署用共享内存，目标比 ROS/ROS2 快 10 倍
- **CLI 单一工具**：`dora run`（本地）、`dora up/start`（分布式）、build、logs、record/replay 都在一个 CLI
- **Hot reload**：Python operator 支持热重载，不用重启 dataflow
- **Fault tolerance**：每节点重启策略（never/on-failure/always）、指数退避、健康监控、熔断器
- **Soft real-time**：可选 `--rt` flag（mlockall + SCHED_FIFO），支持 cpu_affinity
- **OpenTelemetry**：内置结构化日志、metrics、分布式 tracing
- **Record/replay**：`.drec` 文件录制，可离线回放
- **资源监控**：`dora top` TUI 显示每节点 CPU/memory/queue/网络IO

### 安装方式（最常被写错）
```bash
# CLI（Rust 工具链装）
cargo install dora-cli

# Python 节点 API（注意包名！）
pip install dora-rs        # ✅ 正确
pip install dora           # ❌ 错误，这是另一个无关的包

# 导入名是 dora（不是 dora-rs）
from dora import Node      # ✅ 正确
```

### 一键安装脚本
```bash
# Linux/Mac
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.ps1 | iex"
```

### 官方资源
- 英文官网：https://dora-rs.ai/
- GitHub：https://github.com/dora-rs/dora
- 协议：基于 Apache 2.0

---

## 2. DoraMate 项目核心信息

### 是什么
**DoraMate** 是基于 Dora-rs 框架开发的**低代码机器人开发平台**。

定位：把 Dora 这个底层技术框架转化为对开发者更友好的产品形态，通过**可视化节点编排**降低机器人开发门槛。

### 核心价值主张
- **可视化拖拽**：把 Dora 的 YAML dataflow 用图形化方式编排
- **降低门槛**：让没接触过机器人开发的开发者也能上手
- **保留底层能力**：底层依然是高性能的 Dora，不是玩具

### 团队与背景
- **导师**：李扬（echoli.cn）—— Dora-rs 核心维护者之一，2025 年发起 Dora 中文社区
- **学员**：夏豪（开发者增长工程师，前端+SEO+技术博客）、冯小婷（具身智能产品设计师，UI/UX+视频+设计）
- **支持方**：源起之道 | Upstream Labs（这必须在所有公开材料里标注）
- **GitHub**：https://github.com/DoraCN/DoraMate
- **官网**：https://doracc.com

### 与 dora-rs 的关系
DoraMate 是 dora-rs 中文生态的一部分，**不是 dora 的替代品**，而是它的**低代码上层产品**。写文章时要明确这一点，避免误导读者认为 DoraMate 取代了 dora。

---

## 3. 具身智能（Embodied AI）背景知识

### 概念定义
具身智能 = AI + 物理实体（机器人）。区别于纯软件 AI，强调智能体与物理世界的交互能力。

### 为什么现在火
- 大模型（LLM/VLM）让机器人有了"通用大脑"
- 机器人硬件成本下降（Figure、Unitree、宇树等）
- 数据驱动的端到端学习方法成熟（如 RT-2、π0）

### 主流框架对比
| 框架 | 语言 | 特点 |
|---|---|---|
| ROS 2 | C++/Python | 老牌、生态全、但臃肿、实时性一般 |
| Dora-rs | Rust + 多语言 | 新兴、轻量、低延迟、声明式 |
| Isaac ROS | C++ | NVIDIA 生态，需要 NVIDIA 硬件 |

### Dora 在具身智能中的定位
适合做**多模态感知 → 决策 → 控制**的快速 dataflow 编排。
典型应用：自动驾驶感知、机器人操作（manipulation）、人形机器人控制。

---

## 4. 写作禁区（容易写错的事实）

### ❌ 不要这样说
- "DORA 是 Python 框架" → ✅ Dora 核心是 Rust 写的，Python 是节点 API 之一
- "DoraMate 取代了 ROS" → ✅ DoraMate 是基于 Dora 的上层工具，Dora 才是 ROS 的替代候选
- "Dora 是 Coinbase 开发的" → ❌ 千万别！x402 才是 Coinbase 的，Dora-rs 是开源社区维护的
- "pip install dora 安装" → ✅ 应是 `pip install dora-rs`
- "Dora 是清华开发的" → ❌ Dora-rs 是国际开源项目，李扬是核心维护者之一

### ✅ 写作时这样表达
- "Dora-rs 是基于 Rust 的开源机器人中间件"
- "DoraMate 基于 Dora 框架，提供可视化的低代码开发体验"
- "DoraMate 项目是 Dora 中文社区的一部分，由 Upstream Labs 支持"

---

## 5. 内容标准结尾模板

每篇文章/视频结尾必须包含以下信息（具体格式按平台调整）：

```
---
🔗 项目链接：
- GitHub: https://github.com/DoraCN/DoraMate
- Dora 中文社区: https://doracc.com
- Dora 官方: https://dora-rs.ai

源起之道支持｜Supported by Upstream Labs
```
