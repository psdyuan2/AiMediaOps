#!/usr/bin/env python3
"""
Agent系统使用示例
演示如何快速创建和使用Agent
"""

import asyncio
from typing import Any
from pydantic import BaseModel

from app.agents import BaseAgent
from app.core import Context, LLMService


class SimpleResponse(BaseModel):
    """简单的响应模型"""
    message: str
    success: bool
    data: dict[str, Any]


class MyAgent(BaseAgent):
    """自定义Agent示例"""

    @BaseAgent.tool(name="analyze_data", description="分析输入数据")
    def analyze_data(self, data: str) -> dict[str, Any]:
        """分析数据的工具"""
        return {
            "input_length": len(data),
            "word_count": len(data.split()),
            "sentiment": "positive" if "好" in data else "neutral"
        }

    @BaseAgent.tool(name="generate_summary", description="生成内容摘要")
    def generate_summary(self, content: str) -> str:
        """生成摘要的工具"""
        return f"摘要: {content[:50]}..." if len(content) > 50 else f"摘要: {content}"

    async def run(self) -> SimpleResponse:
        """Agent的主执行逻辑"""
        try:
            # 使用工具
            analysis = await self.call_tool("analyze_data", "这是一个很好的测试数据")
            summary = await self.call_tool("generate_summary", "这是一个很长的测试内容，用来测试工具功能和Agent系统的集成效果")

            # 使用LLM生成响应
            llm_response = await self.llm.generate(
                prompt="作为AI助手，总结你刚刚执行的操作",
                response_model=SimpleResponse,
                system_prompt="你是一个功能完整的AI Agent"
            )

            return llm_response

        except Exception as e:
            return SimpleResponse(
                message=f"执行失败: {e}",
                success=False,
                data={"error": str(e)}
            )


async def main():
    """主函数"""
    print("🚀 Agent系统使用示例")
    print("=" * 40)

    # 初始化组件
    llm_service = LLMService()
    context = Context.create_new("演示Agent功能")

    # 创建Agent
    agent = MyAgent(context, llm_service)
    print(f"✅ Agent创建成功: {agent}")
    print(f"🔧 可用工具: {agent.list_tools()}")

    # 运行Agent
    print("\n🤖 运行Agent...")
    result = await agent.run()

    print(f"\n📋 执行结果:")
    print(f"消息: {result.message}")
    print(f"成功: {result.success}")
    print(f"数据: {result.data}")

    print(f"\n✨ 示例完成!")


if __name__ == "__main__":
    asyncio.run(main())