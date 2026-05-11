"""
示例：用 Python 直接调用创作 Agent

适合需要更细粒度控制的场景，比如批量生成、与其他系统集成。

运行：
    python examples/example_create.py
"""
import logging
from doramate_agent.agents import CreatorAgent

logging.basicConfig(level=logging.INFO)


def main():
    # 创建 Agent（自动加载配置和知识库）
    agent = CreatorAgent()
    
    # 单次调用
    result = agent.run(
        topic="DoraMate 拖拽节点教程：5 分钟搭建机器人控制流",
        platforms=["csdn", "xiaohongshu"],   # 只生成两个平台
        user_hint="第一人称视角，强调上手简单",
        contributor_id="fengxiaoting",        # 用冯小婷的人设
    )
    
    print(f"\n生成完成：{result.success_count}/{len(result.results)} 成功")
    print(f"总成本：¥{result.total_cost_cny:.4f}")
    
    for r in result.results:
        if r.success:
            print(f"  ✓ {r.platform_name}: {r.file_path}")
        else:
            print(f"  ✗ {r.platform_name}: {r.error}")


def batch_example():
    """批量示例：一次跑多个主题"""
    agent = CreatorAgent()
    
    topics = [
        "5 分钟看懂 dora-rs",
        "DoraMate UI 设计幕后",
        "为什么我说低代码不是给小白的工具",
    ]
    
    for topic in topics:
        print(f"\n→ 生成主题：{topic}")
        result = agent.run(topic=topic, platforms=["xiaohongshu"])
        print(f"  完成（¥{result.total_cost_cny:.4f}）")


if __name__ == "__main__":
    main()
    # batch_example()   # 取消注释跑批量
