"""
MasterAgent 使用示例

这个文件展示了如何创建和使用 MasterAgent，包括：
- 基本初始化和配置
- 子Agent管理
- 记忆功能使用
- 任务委托和协调
"""

from Agent.master_agent.master_agent_core import MasterAgent
from Agent.Agent import Agent, HttpLLM, OpenAILLM
from Agent.Context import AgentContext
from Agent.Tool import ToolRegistry
from typing import Any, Dict


def create_sample_llm() -> HttpLLM:
    """创建示例LLM实例"""
    # 这里使用 HttpLLM 作为示例，你可以根据需要替换为 OpenAILLM 或其他实现
    return HttpLLM(
        api_url="https://api.example.com/v1/chat/completions",
        api_key="your-api-key-here",
        model="gpt-4"
    )


def setup_sample_tools() -> ToolRegistry:
    """设置示例工具"""
    tools = ToolRegistry()

    # 示例工具：计算器
    @tools.register("calculator", "执行基本数学运算")
    def calculator(expression: str) -> float:
        """计算数学表达式"""
        try:
            return eval(expression)  # 注意：生产环境中应该使用更安全的表达式解析器
        except:
            return "Invalid expression"

    # 示例工具：获取当前时间
    @tools.register("get_time", "获取当前时间")
    def get_time() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 示例工具：文件操作
    @tools.register("read_file", "读取文件内容")
    def read_file(filename: str) -> str:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"文件 {filename} 不存在"
        except Exception as e:
            return f"读取文件错误: {str(e)}"

    return tools


def create_sub_agents(llm) -> Dict[str, Agent]:
    """创建子Agent"""
    sub_agents = {}

    # 创建专门的写作Agent
    writing_context = AgentContext()
    writing_context.add_message("system", "你是一个专业的写作助手，擅长创作和编辑文本。")
    writing_agent = Agent(llm, writing_context)
    sub_agents["writer"] = writing_agent

    # 创建专门的分析Agent
    analysis_context = AgentContext()
    analysis_context.add_message("system", "你是一个数据分析专家，擅长处理和分析数据。")
    analysis_agent = Agent(llm, analysis_context)
    sub_agents["analyst"] = analysis_agent

    return sub_agents


def basic_master_agent_example():
    """基本的 MasterAgent 使用示例"""
    print("=== 基本 MasterAgent 示例 ===")

    # 创建LLM
    llm = create_sample_llm()

    # 设置工具
    tools = setup_sample_tools()

    # 创建MasterAgent
    master_agent = MasterAgent(
        llm=llm,
        tools=tools,
        max_tasks=5,
        memory_enabled=True
    )

    # 运行简单任务
    result = master_agent.run("使用计算器工具计算 123 + 456")
    print(f"任务结果: {result}")

    # 查看Agent统计信息
    stats = master_agent.get_agent_stats()
    print(f"Agent统计: {stats}")


def sub_agent_delegation_example():
    """子Agent委托示例"""
    print("\n=== 子Agent委托示例 ===")

    # 创建LLM
    llm = create_sample_llm()

    # 创建MasterAgent
    master_agent = MasterAgent(llm=llm, memory_enabled=True)

    # 创建子Agent
    sub_agents = create_sub_agents(llm)

    # 添加子Agent
    for name, agent in sub_agents.items():
        master_agent.add_sub_agent(name, agent)
        print(f"添加子Agent: {name}")

    # 直接委托任务给子Agent
    result = master_agent.delegate_to_sub_agent("writer", "写一段关于AI的简短介绍")
    print(f"委托结果: {result}")


def memory_management_example():
    """记忆管理示例"""
    print("\n=== 记忆管理示例 ===")

    # 创建MasterAgent
    master_agent = MasterAgent(
        llm=create_sample_llm(),
        memory_enabled=True
    )

    # 存储记忆
    master_agent.store_memory("user_preference", "喜欢简洁的回答", "user")
    master_agent.store_memory("project_name", "AI助手项目", "project")
    master_agent.store_memory("last_task", "数据分析任务", "tasks")

    # 检索记忆
    preference = master_agent.retrieve_memory("user_preference", "user")
    print(f"用户偏好: {preference}")

    project = master_agent.retrieve_memory("project_name", "project")
    print(f"项目名称: {project}")

    # 列出所有记忆
    all_memories = master_agent.list_memories()
    print(f"所有记忆类别: {list(all_memories.keys())}")


def task_management_example():
    """任务管理示例"""
    print("\n=== 任务管理示例 ===")

    # 创建MasterAgent（设置较小的最大任务数来演示队列功能）
    master_agent = MasterAgent(
        llm=create_sample_llm(),
        max_tasks=2,
        memory_enabled=True
    )

    # 创建多个任务
    task1_id = master_agent.create_task("高优先级任务1", "high")
    task2_id = master_agent.create_task("中优先级任务2", "medium")
    task3_id = master_agent.create_task("低优先级任务3", "low")

    print(f"创建了任务: {task1_id[:8]}...")
    print(f"创建了任务: {task2_id[:8]}...")
    print(f"创建了任务: {task3_id[:8]}...")

    # 查看任务状态
    for task_id in [task1_id, task2_id, task3_id]:
        status = master_agent.get_task_status(task_id)
        print(f"任务 {task_id[:8]}... 状态: {status}")

    # 查看统计信息
    stats = master_agent.get_agent_stats()
    print(f"当前统计: {stats}")


def enhanced_run_example():
    """增强运行方法示例"""
    print("\n=== 增强运行方法示例 ===")

    # 创建MasterAgent
    master_agent = MasterAgent(
        llm=create_sample_llm(),
        tools=setup_sample_tools(),
        memory_enabled=True
    )

    # 使用增强运行方法
    result = master_agent.run_enhanced(
        task="使用get_time工具获取当前时间，然后记住这个操作",
        use_memory=True,
        enable_delegation=True
    )

    print(f"增强运行结果: {result}")


def main():
    """运行所有示例"""
    print("MasterAgent 功能演示")
    print("=" * 50)

    # 注意：由于这些示例需要真实的LLM连接，在实际运行时需要配置正确的API
    # 这里主要展示代码结构和用法

    try:
        basic_master_agent_example()
        sub_agent_delegation_example()
        memory_management_example()
        task_management_example()
        enhanced_run_example()
    except Exception as e:
        print(f"示例运行出错（这是正常的，因为没有配置真实的API）: {e}")
        print("请配置正确的LLM API后再次运行示例。")


if __name__ == "__main__":
    main()


# ===== 配置说明 =====
"""
要运行这些示例，你需要：

1. 安装依赖：
   pip install requests pydantic

2. 配置LLM：
   - 对于OpenAI: 使用 OpenAILM 类，提供有效的 api_key 和 base_url
   - 对于其他API: 使用 HttpLLM 类，配置正确的 api_url 和 api_key

3. 示例LLM配置：
   # OpenAI 示例
   llm = OpenAILM(
       api_key="your-openai-api-key",
       base_url="https://api.openai.com/v1",
       model="gpt-4"
   )

   # DeepSeek 示例
   llm = OpenAILM(
       api_key="your-deepseek-api-key",
       base_url="https://api.deepseek.com/v1",
       model="deepseek-chat"
   )

4. MasterAgent 特性说明：
   - 多任务管理：支持任务队列和优先级处理
   - 子Agent委托：可以将任务委托给专门的子Agent
   - 长期记忆：支持分类存储和检索记忆
   - 增强运行：集成了记忆和委托功能的完整运行流程
   - 统计监控：提供详细的运行统计信息

5. 扩展建议：
   - 可以添加更多专门的子Agent（如图片处理、数据分析等）
   - 可以实现记忆持久化（保存到数据库）
   - 可以添加任务结果缓存机制
   - 可以实现更复杂的工作流程编排
"""