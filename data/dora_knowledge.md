# Dora 知识库(Agent 内置参考)

> 这个文件是创作 Agent 的"事实校验源"。每次生成内容前,Agent 会把这里的关键信息塞进 Prompt,避免胡说。
> 维护原则:发现 Agent 写错了什么,就来这里补充正确版本。

---

## 1. Dora-rs 项目核心信息

### 是什么
DORA = **Dataflow-Oriented Robotic Architecture**(数据流导向的机器人架构)

是一个**基于 Rust 的开源机器人中间件**,目标是简化 AI 机器人应用的开发。它把机器人应用建模为**有向图(pipeline)**,由可组合的节点(node)通过类型化的输入/输出连接而成。

### 关键技术特点(千万别写错)
- **多语言节点**:原生支持 Rust、Python、C、C++(不是 wrapper,是 native API),可在一个 dataflow 里混用
- **声明式 YAML**:用 YAML 定义 dataflow,节点之间通过 typed inputs/outputs 连接
- **低延迟**:同机部署用共享内存,目标比 ROS/ROS2 快 10 倍
- **CLI 单一工具**:`dora run`(本地)、`dora up/start`(分布式)、build、logs、record/replay 都在一个 CLI
- **Hot reload**:Python operator 支持热重载,不用重启 dataflow
- **Fault tolerance**:每节点重启策略(never/on-failure/always)、指数退避、健康监控、熔断器
- **Soft real-time**:可选 `--rt` flag(mlockall + SCHED_FIFO),支持 cpu_affinity
- **OpenTelemetry**:内置结构化日志、metrics、分布式 tracing
- **Record/replay**:`.drec` 文件录制,可离线回放
- **资源监控**:`dora top` TUI 显示每节点 CPU/memory/queue/网络IO

### 安装方式(最常被写错)
```bash
# CLI(Rust 工具链装)
cargo install dora-cli

# Python 节点 API(注意包名!)
pip install dora-rs        # ✅ 正确
pip install dora           # ❌ 错误,这是另一个无关的包

# 导入名是 dora(不是 dora-rs)
from dora import Node      # ✅ 正确
```

### 官方资源
- 英文官网:https://dora-rs.ai/
- GitHub:https://github.com/dora-rs/dora
- 协议:基于 Apache 2.0

---

## 2. DoraMate 项目核心信息

### 是什么
**DoraMate** 是基于 Dora-rs 框架开发的**低代码机器人开发平台**(开发中)。

定位:把 Dora 这个底层技术框架转化为对开发者更友好的产品形态,通过**可视化节点编排**降低机器人开发门槛。

### 🚨 当前真实形态(必须严格遵守,这些是事实禁区)

| 功能 | 状态 | 不能这样写 |
|---|---|---|
| 拖拽式可视化编辑器 | ⏳ 设计阶段,未完成 | ❌ "打开 DoraMate 网页版"、"在 DoraMate 里拖拽节点" |
| 节点市场 | ⏳ 未实现 | ❌ "DoraMate 内置 YOLO、OpenCV、ROS 桥接节点" |
| 一键部署 | ⏳ 未实现 | ❌ "一键启动 dataflow" |
| 实时监控界面 | ⏳ 未实现 | ❌ "DoraMate 的 TUI 监控直接嵌入可视化界面" |
| 产品 UI | ⏳ 设计稿阶段 | ❌ "产品 UI 截图"、"实机截图" |
| 自动 YAML 生成器 | ⏳ 概念阶段 | ❌ "DoraMate 自动生成 YAML 和节点代码模板" |
| 中文社区站点 | ✅ 已上线 | ✅ 可以说"已部署在 doracc.com" |
| Agent 工具 v0.2 | ✅ 已开源 | ✅ 可以说"内容生产 Agent 已开源" |

### ✅ 描述 DoraMate 当前形态的正确措辞

- "DoraMate 是一个**正在开发中的**低代码机器人开发平台"
- "**目标是**提供可视化节点编排"(强调目标,不是现状)
- "**计划支持**拖拽式 dataflow 编辑"
- "**未来将集成**节点市场、实时监控等功能"
- "**当前阶段**主要在 dora-rs 中文文档、教程、社区建设、内容运营基础设施(Agent)上"

### ✅ 描述规划功能时的安全边界

- 可以说"设计目标"、"规划方向"、"正在探索",不要写成产品能力。
- 可以说"我在设计稿里尝试表达节点、连线、参数面板",不要写"已经支持双向同步、hover 提示、自动生成 YAML"。
- 可以说"未来希望降低手写 YAML 的重复劳动",不要说"不需要写一行代码"。
- 可以说"如果后续有节点生态,可以考虑复用常见算法节点",不要具体承诺"内置 YOLO/OpenCV/ROS 桥接节点"。
- 讨论 dora-rs 真实能力时要明确主语是 dora-rs,不要把 `dora run`、`dora top`、record/replay 写成 DoraMate 已有功能。
- 性能数据只能使用知识库已有表述,例如"目标比 ROS/ROS2 快 10 倍";不要编造 `<100μs`、`0.1ms`、具体 fps、具体延迟等未给出的数字。

### 不要假装的事
- ❌ 不要写"我打开 DoraMate,拖出 4 个节点"——你没真做过这个动作
- ❌ 不要写"DoraMate 的 UI 截图"——你只有设计稿
- ❌ 不要写"点击运行,机器人动了起来"——还没接入真实硬件演示
- ❌ 不要编造产品已经具备的功能
- ❌ 不要编造采访、用户 quote、开发者反馈、团队合影、发布会现场、真实 demo 记录
- ❌ 不要写"我用 Rust 搭了机器人框架"——冯小婷不是 dora-rs 作者,也不是算法/底层开发者

### 团队与背景
- **导师**:李扬(echoli.cn)—— Dora-rs 核心维护者之一,2025 年发起 Dora 中文社区
- **学员**:
  - **冯小婷**:产品/UX 设计师(UI、视觉、视频、内容运营)
  - **夏豪**:前端开发(SEO、技术博客、dora-cn 网站)
- **支持方**:源起之道 | Upstream Labs(这必须在所有公开材料里标注)

### 项目链接(在 project.yaml 里统一配置,这里仅供 Agent 校对)
- DoraMate 主项目:见 project.yaml 的 project.github
- Agent 仓库:https://github.com/koljiu753/doramate-media-AI-Agent
- 官网:doracc.com
- dora-cn 中文社区站:https://koljiu753.github.io/dora-cn/

### 与 dora-rs 的关系
DoraMate 是 dora-rs 中文生态的一部分,**不是 dora 的替代品**,而是它的**低代码上层产品**。写文章时要明确这一点,避免误导读者认为 DoraMate 取代了 dora。

---

## 3. 具身智能(Embodied AI)背景知识

### 概念定义
具身智能 = AI + 物理实体(机器人)。区别于纯软件 AI,强调智能体与物理世界的交互能力。

### 为什么现在火
- 大模型(LLM/VLM)让机器人有了"通用大脑"
- 机器人硬件成本下降(Figure、Unitree、宇树等)
- 数据驱动的端到端学习方法成熟(如 RT-2、π0)

### 主流框架对比
| 框架 | 语言 | 特点 |
|---|---|---|
| ROS 2 | C++/Python | 老牌、生态全、但臃肿、实时性一般 |
| Dora-rs | Rust + 多语言 | 新兴、轻量、低延迟、声明式 |
| Isaac ROS | C++ | NVIDIA 生态,需要 NVIDIA 硬件 |

### Dora 在具身智能中的定位
适合做**多模态感知 → 决策 → 控制**的快速 dataflow 编排。
典型应用:自动驾驶感知、机器人操作(manipulation)、人形机器人控制。

---

## 4. 团队成员身份卡(Agent 写内容时必须遵守的视角)

### 冯小婷(本人)
- **身份**:DoraMate 项目的产品/UX 设计师
- **绝对不能假装的身份**:
  - ❌ 不是学生(已经在做项目了,不要写"我在学")
  - ❌ 不是算法工程师(不要写"我训练模型"、"我调参数")
  - ❌ 不是 ROS 老用户(不要写"被 ROS 折磨"这种"经历"
  - ❌ 不是 dora-rs 核心维护者(那是李扬,不是你)
- **正确视角**:
  - ✅ 产品设计师在做 DoraMate 这个项目
  - ✅ UI/UX 设计、视觉规范、交互设计
  - ✅ 内容运营、社区建设
  - ✅ 工具沉淀(Agent 工具开源)
- **写作语气**:
  - 真实、克制、有审美感
  - 不夸张("绝绝子"、"救命"、"yyds" 一律不用)
  - 偏向"我在做"而不是"我在用"或"我在学"

### 夏豪
- **身份**:DoraMate 项目的前端开发工程师
- **正确视角**:技术博客、SEO、前端工程、网站部署

### 李扬(导师)
- **身份**:dora-rs 核心维护者,Dora 中文社区发起人
- **写作时如何提及**:可以说"项目导师"、"dora 中文社区发起人",不要假装是直接合作伙伴

---

## 5. 知乎/CSDN 等内容里身份一致性规则

如果一篇文章里要表达"我"的观点:

- **可以说**:"我是冯小婷,DoraMate 项目的产品设计师" / "项目组在做..." / "我们 team 决定..."
- **不能说**:"我和团队决定基于 Dora-rs 做..."(这是创始人口吻,你是执行者)
- **不能说**:"三个月前我们启动了 DoraMate"(项目时间线不一定对得上,容易翻车)

一篇文章中**身份必须一致**:要么全程"项目成员"视角,要么全程"项目组"视角,不要混用。

---

## 6. 写作禁区(容易写错的事实清单)

### ❌ 不要这样说
- "DORA 是 Python 框架" → ✅ Dora 核心是 Rust 写的,Python 是节点 API 之一
- "DoraMate 取代了 ROS" → ✅ DoraMate 是基于 Dora 的上层工具,Dora 才是 ROS 的替代候选
- "Dora 是 Coinbase 开发的" → ❌ 千万别!x402 才是 Coinbase 的,Dora-rs 是开源社区维护的
- "pip install dora 安装" → ✅ 应是 `pip install dora-rs`
- "Dora 是清华开发的" → ❌ Dora-rs 是国际开源项目,李扬是核心维护者之一
- "我打开 DoraMate 网页版" → ❌ DoraMate 当前没有网页版
- "DoraMate 自带 YOLO 检测节点" → ❌ 节点市场未实现
- "我刚跑通了 DoraMate 抓取演示" → ❌ 真实硬件演示还没做
- "我们采访了一位正在试用 dora-rs 的开发者" → ❌ 除非用户明确提供采访素材
- "我用 Rust 搭了个机器人框架" → ❌ 身份错位,dora-rs 不是冯小婷开发的
- "不需要写一行代码就能搭完整机器人应用" → ❌ 过度承诺,当前没有可视化产品

### ✅ 写作时这样表达
- "Dora-rs 是基于 Rust 的开源机器人中间件"
- "DoraMate 基于 Dora 框架,目标是提供可视化的低代码开发体验(开发中)"
- "DoraMate 项目是 Dora 中文社区的一部分,由 Upstream Labs 支持"

---

## 7. 内容标准结尾模板

每篇文章/视频结尾必须包含以下信息(具体格式按平台调整):

```
---
🔗 项目链接:
- DoraMate 主项目: {project_github}
- Agent 工具(已开源): https://github.com/koljiu753/doramate-media-AI-Agent
- Dora 中文社区: https://koljiu753.github.io/dora-cn/
- Dora 官方: https://dora-rs.ai

源起之道支持｜Supported by Upstream Labs
```

> 注:具体 GitHub 链接以 project.yaml 配置为准,Agent 自动注入。
