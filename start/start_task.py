"""
小红书智能体测试脚本

本脚本演示如何使用XiaohongshuAgent进行小红书操作。
需要先启动小红书MCP服务（端口18060）。

测试步骤：
1. 初始化XiaohongshuAgent（需要Context和LLMService）
2. 建立MCP连接
3. 登录小红书（二维码扫码）
4. 测试基本工具调用
5. 清理资源

注意：本测试会实际调用MCP服务，请确保服务已启动且网络通畅。
"""

import asyncio
import sys
import time
from pathlib import Path
# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))
from app.data.constants import SYS_TYPE, DEFAULT_TASK_TYPE
from app.core.context import Context
from app.core.llm import LLMService
from app.agents.xiaohongshu import XiaohongshuAgent
from app.manager.task_manager import TaskManager


async def main():
    """
    主测试函数

    运行所有测试用例
    """
    task_test = TaskManager(
        sys_type=SYS_TYPE.MAC_INTEL.value,
        task_type=DEFAULT_TASK_TYPE.XHS_TYPE,
        xhs_account_id='94267098699',
        xhs_account_name='花语堂',
        user_query='start',
        user_topic='start',
        user_style='start',
        user_target_audience='start',
        interval=200,
        valid_time_rage=[8, 24],
        task_id=None
    )
    await task_test.run()
    time.sleep(100)
    print("任务暂停")
    task_test.task_pause()



if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(main())