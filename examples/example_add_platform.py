"""
示例：如何加一个新平台（即刻 jike）

这个文件不会真的运行——它只是说明性的注释。

【步骤】

1️⃣ 创建 plugins/platforms/jike.yaml：

```yaml
id: "jike"
name: "即刻"
display_name: "即刻"
enabled: true

profile:
  audience: "互联网产品/创业人群"
  content_type: "short_thought"
  preferred_length: "100-300 字"
  language: "zh-CN"

style:
  tone: "犀利、有观点、节奏感强"
  formatting: "短段落，有金句"
  emoji_density: "low"
  first_person: true
  hashtags: false

seo:
  enabled: false

prompt_template: "prompts/platforms/jike.txt"

publishing:
  has_official_api: false
  manual_url: "https://web.okjike.com"

required_elements:
  - sponsor_attribution_short

output:
  file_extension: "md"
```


2️⃣ 创建 prompts/platforms/jike.txt：

```
你是 {project_name} 项目的内容运营，正在写一条即刻动态。

【知识库】
{knowledge_base}

【主题】
{topic}

【风格要求】
1. 短：100-300 字，分 2-4 段
2. 犀利：要有观点、有钩子，不要中庸
3. 节奏：每段 1-3 句话，金句压尾
4. 即刻特色：圈内人能 get 到的梗 / 行业观察
5. 第一人称：可以"我觉得"、"在我看来"

【强制结尾】
最后一行带：
{project_github} | {sponsor_attribution}

【输出】
直接输出动态内容，不要任何解释。
```


3️⃣ 立刻就能用：

```bash
doramate-agent create --topic "..." --platforms jike
```

—— 完全不需要改任何 Python 代码 ✨


【验证】

运行下面这段确认插件被加载了：

```python
from doramate_agent.platforms import get_platform_registry
registry = get_platform_registry()
for p in registry.list_all():
    print(p.id, p.name)
```

应该看到 `jike` 出现在列表里。
"""
