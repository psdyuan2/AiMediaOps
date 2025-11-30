"""
小红书智能体 - 基于 LangChain 版本 ZhipuLLM
使用您优化后的 ZhipuBrowserUseLLM 适配器
"""

import asyncio
import sys
import os
from typing import Optional, Any, Dict, List
import base64
from datetime import datetime

from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.llm.deepseek.chat import ChatDeepSeek
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from browser_use import Agent
from browser_use import Browser
from llm.zhipu_llm import ZhipuBrowserUseLLM

# 导入日志模块
try:
    from utils.logger import get_logger, log_execution_time, log_async_time_decorator, log_performance
    app_logger = get_logger("XHSWebAgent")
except ImportError:
    # 如果无法导入utils模块，使用标准日志
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app_logger = logging.getLogger("XHSWebAgent")

    # 临时装饰器兼容
    def log_async_time_decorator(level="INFO"):
        def decorator(func):
            return func
        return decorator

    def log_execution_time(name, level="INFO"):
        from contextlib import nullcontext
        return nullcontext()


class XHSWebAgent:
    """
    小红书智能体 - 基于 LangChain 版本

    特点：
    - 使用您优化后的 ZhipuBrowserUseLLM
    - 完全兼容 browser-use 接口
    - 支持 Vision 和 Thinking 模式
    - 原生支持工具调用
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_url: Optional[str] = None,
        model_name: str = "glm-4.5v",
        temperature: float = 0.1,
        use_vision: bool = True,
        llm_model_name = "ZHIPU",
        enable_screenshots: bool = True,
        save_screenshots: bool = True,
        screenshot_dir: str = "./screenshots"
    ):
        """初始化小红书智能体"""
        app_logger.debug("开始初始化小红书智能体")

        load_dotenv()
        api_key = api_key if api_key else os.getenv(f"DEEPSEEK_API_KEY")

        app_logger.debug(f"配置参数: model_name={model_name}, temperature={temperature}")
        app_logger.debug(f"截图功能: enable_screenshots={enable_screenshots}, save_screenshots={save_screenshots}")

        self.llm = ChatDeepSeek(
            api_key=api_key,
            temperature=temperature
        )

        # 截图相关配置
        self.enable_screenshots = enable_screenshots
        self.save_screenshots = save_screenshots
        self.screenshot_dir = screenshot_dir

        # 创建截图目录
        if self.save_screenshots and not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
            app_logger.debug(f"创建截图目录: {self.screenshot_dir}")

        app_logger.info("小红书智能体初始化完成")

    def _save_screenshot(self, screenshot_data: str, step: int, action: str = "") -> str:
        """
        保存截图到文件系统

        Args:
            screenshot_data: base64编码的截图数据
            step: 步骤编号
            action: 动作描述

        Returns:
            保存的文件路径
        """
        if not self.save_screenshots or not screenshot_data:
            app_logger.debug("跳过截图保存：截图功能未启用或无截图数据")
            return ""

        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            action_safe = "".join(c for c in action if c.isalnum() or c in (' ', '-', '_')).rstrip()
            action_safe = action_safe[:20] if action_safe else "step"
            filename = f"step_{step:03d}_{action_safe}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            app_logger.debug(f"准备保存截图: {filename}")

            # 解码并保存
            image_data = base64.b64decode(screenshot_data)
            with open(filepath, 'wb') as f:
                f.write(image_data)

            app_logger.info(f"截图保存成功: {filepath}")
            return filepath
        except Exception as e:
            app_logger.error(f"截图保存失败: {e}")
            return ""

    def _create_result_dict(self, history, screenshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        创建包含截图的结果字典

        Args:
            history: Agent执行历史
            screenshots: 截图列表

        Returns:
            包含所有信息的结果字典
        """
        result_dict = {
            "task_result": None,
            "screenshots": screenshots,
            "execution_info": {
                "total_steps": 0,
                "successful": False,
                "errors": [],
                "urls_visited": [],
                "actions_executed": []
            }
        }

        try:
            # 获取最终结果
            if hasattr(history, 'final_result'):
                result_dict["task_result"] = history.final_result()

            # 获取执行信息
            if hasattr(history, 'number_of_steps'):
                result_dict["execution_info"]["total_steps"] = history.number_of_steps()

            if hasattr(history, 'is_successful'):
                result_dict["execution_info"]["successful"] = history.is_successful()

            if hasattr(history, 'has_errors') and history.has_errors():
                result_dict["execution_info"]["errors"] = [str(error) for error in history.errors() if error]

            if hasattr(history, 'urls'):
                result_dict["execution_info"]["urls_visited"] = history.urls()

            if hasattr(history, 'action_names'):
                result_dict["execution_info"]["actions_executed"] = history.action_names()

        except Exception as e:
            print(f"⚠️ 结果解析失败: {e}")

        return result_dict

    @log_async_time_decorator(level="DEBUG")
    async def run_task(
        self,
        task: str,
        extend_prompt: str = "",
        init_url: Optional[str] = "https://www.baidu.com",
        use_local_browser: bool = True,
        max_steps: int = 20,
        vision_use: Optional[bool] = True,
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        执行小红书相关任务（增强版，支持截图）

        Args:
            task: 任务描述
            extend_prompt: 额外系统提示词
            init_url: 初始URL
            use_local_browser: 是否使用本地浏览器
            max_steps: 最大执行步数
            vision_use: 是否使用视觉模式
            headless: 是否无头模式

        Returns:
            包含任务结果和截图的完整字典
        """
        screenshots = []

        app_logger.info("开始执行任务")
        app_logger.debug(f"任务参数: max_steps={max_steps}, vision_use={vision_use}, headless={headless}")
        app_logger.debug(f"任务内容: {task[:200]}...")

        try:
            # 配置浏览器
            browser_config = {}
            if not headless:
                browser_config['headless'] = False
                browser_config['window_size'] = {'width': 1280, 'height': 800}

            # 如果启用截图，确保视觉模式开启
            if self.enable_screenshots:
                vision_use = True
                app_logger.debug("启用截图功能，自动开启视觉模式")

            initial_actions = []
            if init_url:
                initial_actions.append({'navigate': {'url': init_url, 'new_tab': False}})
                initial_actions.append({'wait': {'seconds': 2}})
                app_logger.debug(f"设置初始动作: 访问 {init_url}")

            # 创建Agent - 使用LangChain兼容的LLM
            app_logger.debug("创建Agent实例")
            agent = Agent(
                task=task,
                llm=self.llm,
                use_vision=vision_use,
                extend_system_message=extend_prompt,
                initial_actions=initial_actions,
                generate_gif=self.save_screenshots  # 可选：生成GIF
            )

            app_logger.info("开始执行Agent任务")
            app_logger.info(f"配置信息 - 截图功能: {'启用' if self.enable_screenshots else '禁用'}")
            app_logger.info(f"配置信息 - 保存截图: {'启用' if self.save_screenshots else '禁用'}")

            # 执行任务
            history = await agent.run(max_steps=max_steps)
            app_logger.info("Agent任务执行完成")

            # 收集截图
            if self.enable_screenshots:
                try:
                    if hasattr(history, 'screenshots'):
                        screenshot_data_list = history.screenshots()
                        app_logger.info(f"捕获到 {len(screenshot_data_list)} 张截图")

                        for i, screenshot_data in enumerate(screenshot_data_list):
                            # 获取对应的动作信息
                            action_name = ""
                            if hasattr(history, 'action_names') and i < len(history.action_names()):
                                action_name = history.action_names()[i]

                            app_logger.debug(f"处理第 {i+1} 张截图，动作: {action_name}")

                            # 保存截图
                            saved_path = self._save_screenshot(screenshot_data, i+1, action_name)

                            screenshot_info = {
                                "step": i + 1,
                                "action": action_name,
                                "data": screenshot_data,
                                "saved_path": saved_path,
                                "timestamp": datetime.now().isoformat()
                            }
                            screenshots.append(screenshot_info)

                            if saved_path:
                                app_logger.debug(f"截图已保存: {saved_path}")

                    elif hasattr(history, 'screenshot_paths'):
                        # 如果有直接保存的路径
                        screenshot_paths = history.screenshot_paths()
                        app_logger.info(f"捕获到 {len(screenshot_paths)} 张截图")

                        for i, screenshot_path in enumerate(screenshot_paths):
                            # 读取截图数据
                            try:
                                with open(screenshot_path, 'rb') as f:
                                    screenshot_data = base64.b64encode(f.read()).decode('utf-8')

                                action_name = ""
                                if hasattr(history, 'action_names') and i < len(history.action_names()):
                                    action_name = history.action_names()[i]

                                app_logger.debug(f"处理截图文件: {screenshot_path}, 动作: {action_name}")

                                screenshot_info = {
                                    "step": i + 1,
                                    "action": action_name,
                                    "data": screenshot_data,
                                    "saved_path": screenshot_path,
                                    "timestamp": datetime.now().isoformat()
                                }
                                screenshots.append(screenshot_info)
                                app_logger.debug(f"截图处理成功: {screenshot_path}")
                            except Exception as e:
                                app_logger.error(f"截图处理失败: {e}")

                except Exception as e:
                    app_logger.error(f"截图收集失败: {e}")

            # 创建完整结果
            app_logger.debug("创建执行结果字典")
            result_dict = self._create_result_dict(history, screenshots)

            app_logger.info("任务执行完成")

            # 显示结果摘要
            if result_dict["task_result"]:
                result_preview = str(result_dict["task_result"])[:300]
                app_logger.info(f"结果预览: {result_preview}...")

            if screenshots:
                app_logger.info(f"过程截图: {len(screenshots)} 张")

            app_logger.info(f"执行步数: {result_dict['execution_info']['total_steps']}")
            app_logger.info(f"执行状态: {'成功' if result_dict['execution_info']['successful'] else '失败'}")

            return result_dict

        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            app_logger.error(error_msg)
            app_logger.exception("任务执行异常详情")

            # 返回错误结果
            return {
                "task_result": None,
                "screenshots": screenshots,
                "execution_info": {
                    "total_steps": 0,
                    "successful": False,
                    "errors": [str(e)],
                    "urls_visited": [],
                    "actions_executed": []
                }
            }

    # 便捷方法
    async def explore_homepage(self, **kwargs) -> Dict[str, Any]:
        """探索小红书首页"""
        app_logger.info("执行便捷方法：探索小红书首页")
        task = f"""
        访问小红书首页: https://www.xiaohongshu.com

        请详细观察并分析：
        1. 页面是否成功加载
        2. 主要内容布局和设计特点
        3. 推荐内容的类型和主题
        4. 用户界面元素的分布
        5. 是否有登录提示或限制
        6. 热门话题或标签的存在

        请提供详细的结构化分析报告。
        """
        return await self.run_task(task, init_url="https://www.xiaohongshu.com", use_local_browser=False, **kwargs)

    async def search_content(self, keyword: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """搜索小红书内容"""
        app_logger.info(f"执行便捷方法：搜索小红书内容，关键词: {keyword}")
        task = f"""
        在小红书上搜索关键词: {keyword}

        请执行以下详细操作：
        1. 访问小红书首页
        2. 找到搜索功能并输入关键词: {keyword}
        3. 执行搜索操作
        4. 分析搜索结果页面的内容
        5. 提取前 {max_results} 个搜索结果的详细信息：
           - 帖子标题
           - 作者信息
           - 点赞数、评论数、收藏数
           - 内容类型和标签
           - 内容简要描述

        请提供结构化的搜索结果报告。
        """
        return await self.run_task(task, init_url="https://www.xiaohongshu.com", use_local_browser=False, **kwargs)

    async def analyze_post(self, post_url: str, **kwargs) -> Dict[str, Any]:
        """分析特定帖子"""
        app_logger.info(f"执行便捷方法：分析小红书帖子，URL: {post_url}")
        task = f"""
        分析小红书帖子: {post_url}

        请提供深度分析：
        1. 帖子基本信息（标题、作者、发布时间）
        2. 内容主题和分类
        3. 视觉内容分析（如果包含图片）
        4. 用户互动情况（点赞、评论、收藏）
        5. 内容质量和创作特点
        6. 目标受众分析
        7. 标签和话题使用情况
        8. 内容的潜在影响力和传播性

        请提供专业的分析报告。
        """
        return await self.run_task(task, init_url=post_url, **kwargs)

    async def analyze_trends(self, category: str = "推荐", **kwargs) -> Dict[str, Any]:
        """分析热门趋势"""
        task = f"""
        分析小红书 {category} 分类的热门趋势：

        1. 访问小红书首页并浏览 {category} 内容
        2. 观察热门帖子的共同特征
        3. 分析内容类型分布
        4. 识别当前流行的话题和标签
        5. 分析用户互动模式
        6. 总结内容趋势和用户偏好
        7. 预测可能的内容发展方向

        请提供详细的趋势分析报告。
        """
        return await self.run_task(task, init_url="https://www.xiaohongshu.com", use_local_browser=False, **kwargs)

    async def content_research(self, topic: str, depth: str = "shallow", **kwargs) -> Dict[str, Any]:
        """内容研究"""
        if depth == "deep":
            task = f"""
            对小红书上的 {topic} 进行深度研究：

            1. 搜索相关内容并分析热门帖子
            2. 深入分析内容质量和创作技巧
            3. 研究用户互动和反馈模式
            4. 分析内容的商业价值和影响力
            5. 识别关键创作者和意见领袖
            6. 总结成功内容的特点和规律
            7. 提供内容创作和营销建议

            请提供全面的研究报告。
            """
        else:
            task = f"""
            对小红书上的 {topic} 进行基础研究：

            1. 搜索相关内容
            2. 分析内容类型和热度
            3. 观察用户互动情况
            4. 识别主要特点和趋势

            请提供简洁的研究摘要。
            """

        return await self.run_task(task, init_url="https://www.xiaohongshu.com", use_local_browser=False, **kwargs)

    def print_summary(self, result: Dict[str, Any]) -> None:
        """
        打印任务执行结果摘要

        Args:
            result: run_task 返回的结果字典
        """
        print("\n" + "="*50)
        print("📊 任务执行摘要")
        print("="*50)

        if result["task_result"]:
            print("✅ 任务执行成功")
            print(f"📝 结果预览: {str(result['task_result'])[:200]}...")
        else:
            print("❌ 任务执行失败")

        print(f"📈 总步数: {result['execution_info']['total_steps']}")
        print(f"📸 截图数量: {len(result['screenshots'])}")

        if result['execution_info']['successful']:
            print("🎯 执行状态: 成功")
        else:
            print("⚠️ 执行状态: 失败")
            if result['execution_info']['errors']:
                print(f"🚨 错误信息: {result['execution_info']['errors'][0]}")

        if result['execution_info']['urls_visited']:
            print(f"🌐 访问URL数量: {len(result['execution_info']['urls_visited'])}")

        if result['screenshots']:
            print("\n📸 截图列表:")
            for i, screenshot in enumerate(result['screenshots'][:5]):  # 只显示前5个
                action = screenshot.get('action', '未知动作')
                path = screenshot.get('saved_path', '未保存')
                print(f"  {i+1}. 步骤 {screenshot['step']}: {action} -> {path}")
            if len(result['screenshots']) > 5:
                print(f"  ... 还有 {len(result['screenshots']) - 5} 张截图")

        print("="*50)

    def get_screenshot_paths(self, result: Dict[str, Any]) -> List[str]:
        """
        获取所有截图的文件路径

        Args:
            result: run_task 返回的结果字典

        Returns:
            截图文件路径列表
        """
        return [screenshot['saved_path'] for screenshot in result['screenshots'] if screenshot.get('saved_path')]

    def get_screenshots_by_action(self, result: Dict[str, Any], action_pattern: str) -> List[Dict[str, Any]]:
        """
        根据动作模式筛选截图

        Args:
            result: run_task 返回的结果字典
            action_pattern: 动作模式（支持部分匹配）

        Returns:
            匹配的截图列表
        """
        filtered_screenshots = []
        for screenshot in result['screenshots']:
            action = screenshot.get('action', '').lower()
            if action_pattern.lower() in action:
                filtered_screenshots.append(screenshot)
        return filtered_screens


# 便利函数
async def run_xhs_langchain_agent(
    task: str,
    api_key: Optional[str] = None,
    model_name: str = "glm-4.5v",
    thinking_enabled: bool = True,
    use_vision: bool = False,
    **kwargs
):
    """
    便利函数：快速运行小红书智能体 (LangChain版本)

    Args:
        task: 任务描述
        api_key: 智谱AI API密钥
        model_name: 模型名称
        thinking_enabled: 是否启用思考模式
        use_vision: 是否启用视觉模式
        **kwargs: 其他参数

    Returns:
        包含截图的执行结果字典
    """
    agent = XHSWebAgent(
        api_key=api_key,
        model_name=model_name,
        thinking_enabled=thinking_enabled,
        use_vision=use_vision
    )

    return await agent.run_task(task, **kwargs)


# ============================================================
# 测试代码
# ============================================================
if __name__ == "__main__":
    async def test_langchain_xhs_agent():
        """测试LangChain版本的小红书智能体（增强版）"""
        print("🧪 测试 LangChain 版本小红书智能体 (增强版)")
        print("=" * 60)

        try:
            # 创建智能体实例（启用截图功能）
            agent = XHSWebAgent(
                model_name="glm-4.5v",
                thinking_enabled=True,
                use_vision=True,
                enable_screenshots=True,
                save_screenshots=True,
                screenshot_dir="./test_screenshots"
            )
            print("✅ LangChain版智能体创建成功")
            print(f"🧠 思考模式: {agent.llm.thinking_enabled}")
            print(f"🤖 模型: {agent.llm.model_name}")
            print(f"📸 截图功能: {'启用' if agent.enable_screenshots else '禁用'}")
            print(f"💾 截图保存: {'启用' if agent.save_screenshots else '禁用'}")

            # 测试1: 探索首页
            print("\n🆕 测试1: 探索小红书首页")
            result1 = await agent.explore_homepage(headless=True, max_steps=5)

            # 打印详细摘要
            agent.print_summary(result1)

            # 获取截图路径
            screenshot_paths = agent.get_screenshot_paths(result1)
            if screenshot_paths:
                print(f"\n📸 生成的截图文件:")
                for path in screenshot_paths:
                    print(f"  - {path}")

            # 测试2: 分析趋势
            print("\n📊 测试2: 分析热门趋势")
            result2 = await agent.analyze_trends("推荐", headless=True, max_steps=3)
            agent.print_summary(result2)

            # 测试3: 搜索内容
            print("\n🔍 测试3: 搜索美食内容")
            result3 = await agent.search_content("美食推荐", max_results=3, headless=True, max_steps=5)
            agent.print_summary(result3)

            # 展示截图筛选功能
            if result3["screenshots"]:
                print("\n📸 截图筛选示例:")
                click_screenshots = agent.get_screenshots_by_action(result3, "click")
                search_screenshots = agent.get_screenshots_by_action(result3, "search")

                if click_screenshots:
                    print(f"  🖱️ 点击动作截图: {len(click_screenshots)} 张")
                if search_screenshots:
                    print(f"  🔍 搜索动作截图: {len(search_screenshots)} 张")

            print("\n🎉 LangChain版本测试完成!")
            print("📂 所有截图已保存到 ./test_screenshots 目录")

        except Exception as e:
            print(f"❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()

    # 运行测试
    asyncio.run(test_langchain_xhs_agent())