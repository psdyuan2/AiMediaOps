import datetime
import time
import uuid
import shutil
import os
from pathlib import Path
from datetime import date
from diskcache import Cache
from app.data.constants import SYS_TYPE, DEFAULT_TASK_TYPE, COOKIE_TARGET_PATH, DEFAULT_KNOWLEDGE_PATH, TASK_INTERVAL_TIME
from app.agents.xiaohongshu.agent import XiaohongshuAgent
from app.core.llm import LLMService
from app.core.context import Context
from app.core.logger import logger
from app.utils.path_utils import *
from app.manager.task_context import Task_Manager_Context
from typing import List
from app.core.config import APP_DATA_DIR

"""
初始化任务管理器的入参
TaskManager(
    sys_type=SYS_TYPE.MAC_INTEL.value,
    task_type=DEFAULT_TASK_TYPE.XHS_TYPE,
    xhs_account_id='start'
    xhs_account_name='start'
    user_query='start
    user_topic='start
    user_style='start
    user_target_audience='start
    task_id=None
    )
"""

class TaskManager:
    def __init__(self, sys_type, **kwargs):
        """
        如果穿task_id, 则会在context缓存文件中寻找历史任务；否则，创建全新任务
        Args:
            sys_type: 操作系统类型
            task_type: 任务类型，默认是小红书任务
            xhs_account_id: 小红书账户ID（必填）
            xhs_account_name: 小红书账户名称（必填）
            user_query: 用户查询内容（可选）
            user_topic: 帖子主题（可选）
            user_style: 内容风格（可选）
            user_target_audience: 目标受众（可选）
            task_id: 任务ID（可选，不提供则自动生成）
            task_end_time: 任务结束时间，datetime.date格式
        """
        self.task_id = kwargs.get('task_id', None)
        if not self.task_id:
            # 未传入task_id, 构建全新任务
            self.task_id = str(uuid.uuid4())
            self.sys_type = sys_type
            # task_type 应该在接口层已经转换为枚举类型，这里直接使用并验证
            task_type = kwargs.get('task_type', DEFAULT_TASK_TYPE.XHS_TYPE)
            if isinstance(task_type, DEFAULT_TASK_TYPE):
                self.task_type = task_type
            else:
                # 如果不是枚举类型，抛出错误（不应该发生）
                raise ValueError(f"task_type 必须是 DEFAULT_TASK_TYPE 枚举类型，当前类型: {type(task_type)}, 值: {task_type}")
            # 保存小红书相关参数
            self.xhs_account_id = kwargs.get('xhs_account_id')
            self.xhs_account_name = kwargs.get('xhs_account_name')
            self.user_query = kwargs.get('user_query')
            self.user_topic = kwargs.get('user_topic')
            self.user_style = kwargs.get('user_style')
            self.user_target_audience = kwargs.get('user_target_audience')
            # 获取任务参数
            self.task_end_time = kwargs.get('task_end_time', datetime.date.today() + datetime.timedelta(days=30))
            self.interval = kwargs.get('interval', TASK_INTERVAL_TIME)
            self.valid_time_range = kwargs.get('valid_time_range', [8, 22])  # 修复拼写错误：valid_time_rage -> valid_time_range
            # 获取模式，如果没有则使用默认值
            from app.data.constants import TaskMode
            mode_str = kwargs.get('mode', TaskMode.STANDARD.value)
            if isinstance(mode_str, TaskMode):
                self.mode = mode_str
            elif isinstance(mode_str, str):
                try:
                    self.mode = TaskMode(mode_str)
                except ValueError:
                    logger.warning(f"无效的模式值: {mode_str}，使用默认值 {TaskMode.STANDARD.value}")
                    self.mode = TaskMode.STANDARD
            else:
                self.mode = TaskMode.STANDARD
            # 获取互动笔记数量，默认3，限制在1-5之间
            self.interaction_note_count = kwargs.get('interaction_note_count', 3)
            self.interaction_note_count = max(1, min(5, int(self.interaction_note_count))) if self.interaction_note_count else 3
            self.round_num = 0
            # 初始化context
            self.context = Task_Manager_Context(self.task_id)
            # 将 sys_type 传递给 context，以便恢复任务时使用
            kwargs_with_sys_type = {**kwargs, "sys_type": sys_type}
            self.context.create_new_meta(**kwargs_with_sys_type)
        else:
            # 传入task_id, 通过历史缓存构建task
            # 初始化context
            self.context = Task_Manager_Context(self.task_id)
            self.context.create_from_meta()
            # 从context中获取该参数
            # sys_type 从传入参数获取，如果没有则从 context 获取，如果都没有则使用默认值
            self.sys_type = sys_type if sys_type else self.context.get('sys_type', SYS_TYPE.MAC_INTEL.value)
            
            # 恢复 task_type，处理 None 和字符串值
            task_type_value = self.context.get('task_type')
            if task_type_value is None:
                logger.warning(f"任务 {self.task_id} 的 task_type 为 None，使用默认值")
                self.task_type = DEFAULT_TASK_TYPE.XHS_TYPE
            elif isinstance(task_type_value, str):
                if task_type_value == 'xhs_type' or task_type_value == DEFAULT_TASK_TYPE.XHS_TYPE.value:
                    self.task_type = DEFAULT_TASK_TYPE.XHS_TYPE
                else:
                    logger.warning(f"任务 {self.task_id} 的 task_type 值不正确: {task_type_value}，使用默认值")
                    self.task_type = DEFAULT_TASK_TYPE.XHS_TYPE
            elif isinstance(task_type_value, DEFAULT_TASK_TYPE):
                self.task_type = task_type_value
            else:
                logger.warning(f"任务 {self.task_id} 的 task_type 类型不正确: {type(task_type_value)}，使用默认值")
                self.task_type = DEFAULT_TASK_TYPE.XHS_TYPE
            
            # 从 context 的 meta 中恢复小红书相关参数
            self.xhs_account_id = self.context.get('xhs_account_id') or kwargs.get('xhs_account_id')
            self.xhs_account_name = self.context.get('xhs_account_name') or kwargs.get('xhs_account_name')
            self.user_query = self.context.get('user_query') or kwargs.get('user_query')
            self.user_topic = self.context.get('user_topic') or kwargs.get('user_topic')
            self.user_style = self.context.get('user_style') or kwargs.get('user_style')
            self.user_target_audience = self.context.get('user_target_audience') or kwargs.get('user_target_audience')
            # task_end_time 从 context 获取，如果是 None 或字符串 "None"，则使用默认值（30天后）
            task_end_time_value = self.context.get('task_end_time')
            if task_end_time_value is None or task_end_time_value == "None":
                self.task_end_time = datetime.date.today() + datetime.timedelta(days=30)
            elif isinstance(task_end_time_value, str):
                # 如果是字符串，尝试解析为 date 对象
                try:
                    self.task_end_time = datetime.date.fromisoformat(task_end_time_value)
                except (ValueError, TypeError):
                    logger.warning(f"无法解析 task_end_time: {task_end_time_value}，使用默认值（30天后）")
                    self.task_end_time = datetime.date.today() + datetime.timedelta(days=30)
            elif isinstance(task_end_time_value, datetime.date):
                self.task_end_time = task_end_time_value
            else:
                logger.warning(f"task_end_time 类型不正确: {type(task_end_time_value)}，使用默认值（30天后）")
                self.task_end_time = datetime.date.today() + datetime.timedelta(days=30)
            
            # interval 从 context 获取，如果为 None 则使用默认值
            self.interval = self.context.get('interval') or TASK_INTERVAL_TIME
            
            # valid_time_range 从 context 获取
            # None 表示无限制，[start_hour, end_hour] 表示有时间范围限制
            valid_time_range_value = self.context.get('valid_time_range')
            if valid_time_range_value is None:
                # None 表示无限制
                self.valid_time_range = None
            elif isinstance(valid_time_range_value, list) and len(valid_time_range_value) >= 2:
                self.valid_time_range = valid_time_range_value
            else:
                logger.warning(f"任务 {self.task_id} 的 valid_time_range 无效，使用默认值 [8, 22]")
                self.valid_time_range = [8, 22]
            
            # round_num 从 context 获取，如果为 None 则使用默认值 0
            self.round_num = self.context.get('round_num') or 0
            
            # mode 从 context 获取，如果为 None 则使用默认值
            from app.data.constants import TaskMode
            mode_str = self.context.get('mode', TaskMode.STANDARD.value)
            try:
                self.mode = TaskMode(mode_str) if isinstance(mode_str, str) else (mode_str if isinstance(mode_str, TaskMode) else TaskMode.STANDARD)
            except (ValueError, TypeError):
                logger.warning(f"任务 {self.task_id} 的模式值无效: {mode_str}，使用默认值 {TaskMode.STANDARD.value}")
                self.mode = TaskMode.STANDARD
            
            # interaction_note_count 从 context 获取，默认3，限制在1-5之间
            self.interaction_note_count = self.context.get('interaction_note_count', 3)
            self.interaction_note_count = max(1, min(5, int(self.interaction_note_count))) if self.interaction_note_count else 3
        # 初始化暂停开关变量
        tasks_dir = APP_DATA_DIR / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        switch_path = tasks_dir / f"{self.task_id}_task_switch"
        
        self.task_switch = Cache(str(switch_path))
        self.task_resume()
        
        # 检查并确保 MCP 服务正在运行（在初始化 agent 之前）
        self._mcp_service_check()
        
        # 初始化小红书 agent
        self.agent = self._init_agent(**self.context.get_xhs_params())

    def _init_agent(self, **kwargs):
        # task_type 应该已经是枚举类型，直接比较
        if self.task_type == DEFAULT_TASK_TYPE.XHS_TYPE:
            # 检查必填参数
            if not self.xhs_account_id:
                raise ValueError("小红书任务必须提供xhs_account_id参数")
            if not self.xhs_account_name:
                raise ValueError("小红书任务必须提供xhs_account_name参数")

            llm = LLMService()
            context = Context.create_new(goal="智能化小红书运营智能体")

            # 初始化XiaohongshuAgent
            agent = XiaohongshuAgent(
                context=context,
                llm=llm,
                user_name=self.xhs_account_name,
                user_id=self.xhs_account_id,
                task_id=self.task_id,
                user_query=self.user_query,
                user_topic=self.user_topic,
                user_style=self.user_style,
                user_target_audience=self.user_target_audience,
                knowledge_base_path=DEFAULT_KNOWLEDGE_PATH,
                mcp_server_url="http://localhost:18060/mcp",  # 默认值
                mode=self.mode.value if hasattr(self.mode, 'value') else str(self.mode),  # 传递模式
                interaction_note_count=self.interaction_note_count  # 传递互动笔记数量
            )

            # 使用绑定了 task_id 和 bindtype 的 logger 记录日志
            from app.data.constants import LogBindType
            task_logger = logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG)
            task_logger.info(f"小红书智能体初始化成功: user_id={self.xhs_account_id}, task_id={self.task_id}")
            return agent
        else:
            logger.warning(f"未知的任务类型: {self.task_type}")
            return None
    def task_pause(self):
        self.task_switch.set('state', 'PAUSE')
    def task_resume(self):
        self.task_switch.set('state', 'RUNNING')
    def _mcp_service_check(self):
        """
        检查并确保 MCP 服务正在运行
        
        如果服务未运行，会自动启动服务
        """
        from app.utils.mcp_service_manager import MCPServiceManager
        
        try:
            mcp_manager = MCPServiceManager()
            sys_type_str = self.sys_type.value if isinstance(self.sys_type, SYS_TYPE) else str(self.sys_type)
            
            if mcp_manager.ensure_service_running(sys_type=sys_type_str, headless=True):
                logger.info("MCP 服务检查通过，服务正在运行")
            else:
                logger.warning("MCP 服务启动失败，任务可能无法正常执行")
                raise RuntimeError("MCP 服务未运行且启动失败，无法继续执行任务")
        except Exception as e:
            logger.error(f"MCP 服务检查失败: {e}", exc_info=True)
            raise RuntimeError(f"MCP 服务检查失败: {e}")

    def _dispatch_cookies(self, source_path, destination_path):
        """
        分发cookies文件到MCP服务目录

        将用户专属cookies文件复制到MCP服务目录，替换标准cookies文件。

        Args:
            source_path: 用户专属cookies文件路径
            destination_path: MCP服务cookies目录路径

        Raises:
            RuntimeError: 文件检查或复制失败时抛出
        """
        # 1. 验证源文件
        if not os.path.exists(source_path):
            raise RuntimeError(f"源cookies文件不存在: {source_path}")
        if not os.path.isfile(source_path):
            raise RuntimeError(f"源路径不是文件: {source_path}")

        # 2. 验证目标目录
        if not os.path.exists(destination_path):
            raise RuntimeError(f"目标目录不存在: {destination_path}")
        if not os.path.isdir(destination_path):
            raise RuntimeError(f"目标路径不是目录: {destination_path}")

        # 3. 构建目标文件路径
        target_file = os.path.join(destination_path, "cookies.json")

        # 4. 复制文件
        try:
            shutil.copy2(source_path, target_file)
        except Exception as e:
            raise RuntimeError(f"复制cookies文件失败: {e}")

        # 5. 验证复制结果
        if not os.path.exists(target_file):
            raise RuntimeError(f"复制后目标文件不存在: {target_file}")

        file_size = os.path.getsize(target_file)
        if file_size <= 0:
            raise RuntimeError(f"目标文件大小为0: {target_file}")

        logger.info(f"cookies文件分发成功: {source_path} -> {target_file} (大小: {file_size} bytes)")

    def _clear_cookies(self, cookie_path=COOKIE_TARGET_PATH):
        """
        删除当前mcp的cookie文件

        Args:
            cookie_path: cookie文件目录路径，默认为COOKIE_TARGET_PATH

        Returns:
            bool: 删除成功返回True，否则返回False
        """
        source_file = os.path.join(cookie_path, "cookies.json")

        # 检查文件是否存在
        if not os.path.exists(source_file):
            logger.warning(f"cookie文件不存在: {source_file}，跳过删除")
            return False

        if not os.path.isfile(source_file):
            logger.warning(f"cookie路径不是文件: {source_file}，跳过删除")
            return False

        try:
            os.remove(source_file)
            logger.info(f"cookie文件删除成功: {source_file}")
            return True
        except Exception as e:
            logger.error(f"删除cookie文件失败: {e}")
            return False

    def _close_task(self):
        """
        任务执行完成后的收尾工作

        主要功能：
        1. 将MCP服务目录中的cookies.json复制回用户专属目录
        2. 确保用户的cookies文件被更新（如果MCP服务更新了cookies）
        3. 删除xhs_mcp/cookies.json，确保下次执行时需要重新登录
        """
        from app.data.constants import COOKIE_SOURCE_PATH
        
        # 1. 构建路径
        # MCP 服务实际使用的 cookies 路径（xhs_mcp/cookies.json）
        mcp_cookies_file = os.path.join(COOKIE_SOURCE_PATH, "cookies.json")
        user_cookies_dir = get_user_cookies_path(self.xhs_account_id)
        user_cookies_file = os.path.join(user_cookies_dir, "cookies.json")

        # 2. 将 MCP 服务目录中的 cookies 复制回用户专属目录（如果存在）
        # 这样如果 MCP 服务在执行过程中更新了 cookies（如刷新了 token），
        # 更新的 cookies 会被保存到用户专属目录
        if os.path.exists(mcp_cookies_file) and os.path.isfile(mcp_cookies_file):
            try:
                # 确保目标目录存在
                os.makedirs(user_cookies_dir, exist_ok=True)
                # 复制文件
                shutil.copy2(mcp_cookies_file, user_cookies_file)
                logger.info(f"cookies反向复制完成: {mcp_cookies_file} -> {user_cookies_file}")
            except Exception as e:
                logger.error(f"cookies反向复制失败: {e}")
                # 因为是收尾工作，只记录错误不抛出异常
        
        # 3. 删除 xhs_mcp/cookies.json，确保下次执行时需要重新登录
        # 注意：虽然删除了 MCP 目录的 cookies，但用户专属目录的 cookies 已保存
        # 下次执行时，会再次将用户专属目录的 cookies 复制到 MCP 目录
        # 如果用户专属目录的 cookies 仍然有效，则不需要重新登录
        if os.path.exists(mcp_cookies_file) and os.path.isfile(mcp_cookies_file):
            try:
                os.remove(mcp_cookies_file)
                logger.info(f"已删除 MCP cookies: {mcp_cookies_file}")
            except Exception as e:
                logger.warning(f"删除 MCP cookies 失败: {e}")
                # 因为是收尾工作，只记录警告不抛出异常

    def _check_time_valid(self):
        """
        判断小时数是否在范围内（仅限同日，不处理跨夜）。
        
        如果 valid_time_range 为 None，表示无限制，返回 True。

        Args:
            time_range: [开始小时, 结束小时], e.g., [9, 18]，或 None 表示无限制
            target_hour: 待判断的小时数，默认当前时间
        """
        # None 表示无限制，直接返回 True
        if self.valid_time_range is None:
            return True
        
        # 确保 valid_time_range 有效
        if not isinstance(self.valid_time_range, list) or len(self.valid_time_range) < 2:
            logger.warning(f"任务 {self.task_id} 的 valid_time_range 无效，默认返回 True（允许执行）")
            self.valid_time_range = [8, 22]  # 设置默认值
            self.context.save({"valid_time_range": self.valid_time_range})
        
        target_hour = datetime.datetime.now().hour
        start, end = self.valid_time_range[0], self.valid_time_range[1]

        # Python 特有的链式比较，等同于 start <= target_hour and target_hour <= end
        return start <= target_hour <= end
    async def run_once(self, skip_time_check: bool = False) -> bool:
        """
        执行一次任务（单次执行，不包含循环）
        
        每次调用只执行一次任务，然后返回。调度器负责管理任务的生命周期
        和下次执行时间的计算。
        
        Args:
            skip_time_check: 是否跳过时间范围检查（用于立即执行场景）
        
        Returns:
            bool: 是否应该继续执行
                - True: 任务未到期，可以继续调度
                - False: 任务已到期（now >= task_end_time），不应再执行
        """
        # 1. 检查任务是否已到期
        # 确保 task_end_time 不为 None
        if self.task_end_time is None:
            logger.warning(f"任务 {self.task_id} 的 task_end_time 为 None，使用默认值（30天后）")
            self.task_end_time = datetime.date.today() + datetime.timedelta(days=30)
            # 保存更新后的 task_end_time 到 context
            if self.task_end_time:
                self.context.save({"task_end_time": self.task_end_time.isoformat()})
        
        # 再次检查，确保 task_end_time 不为 None（防御性编程）
        if self.task_end_time is None:
            logger.error(f"任务 {self.task_id} 的 task_end_time 仍然为 None，无法继续执行")
            return False
        
        if datetime.date.today() >= self.task_end_time:
            logger.info(f"任务 {self.task_id} 已到期（结束时间: {self.task_end_time}），不再执行")
            return False
        
        # 2. 在执行前重新从context读取最新的mode和interaction_note_count（因为可能在任务执行过程中被更新）
        from app.data.constants import TaskMode, LogBindType
        mode_str = self.context.get('mode', TaskMode.STANDARD.value)
        try:
            updated_mode = TaskMode(mode_str) if isinstance(mode_str, str) else (mode_str if isinstance(mode_str, TaskMode) else TaskMode.STANDARD)
            if updated_mode != self.mode:
                logger.info(f"任务 {self.task_id} 模式已更新: {self.mode.value} -> {updated_mode.value}")
                self.mode = updated_mode
        except (ValueError, TypeError) as e:
            logger.warning(f"任务 {self.task_id} 的模式值无效: {mode_str}，使用当前值 {self.mode.value}")
        
        # 更新互动笔记数量
        updated_interaction_note_count = self.context.get('interaction_note_count', 3)
        updated_interaction_note_count = max(1, min(5, int(updated_interaction_note_count))) if updated_interaction_note_count else 3
        if updated_interaction_note_count != self.interaction_note_count:
            logger.info(f"任务 {self.task_id} 互动笔记数量已更新: {self.interaction_note_count} -> {updated_interaction_note_count}")
            self.interaction_note_count = updated_interaction_note_count
        
        # 3. 检查任务是否是暂停状态
        if self.task_switch.get('state') == 'PAUSE':
            logger.debug(f"任务 {self.task_id} 第 {self.round_num} 轮次暂停，跳过本次执行")
            return True  # 返回True表示任务未到期，但本次因暂停未执行
        
        # 4. 检查任务是否在执行时间区间内（立即执行时跳过此检查）
        if not skip_time_check:
            if not self._check_time_valid():
                logger.debug(f"任务 {self.task_id} 第 {self.round_num} 轮次未执行，不在执行时间范围内")
                return True  # 返回True表示任务未到期，但本次因时间范围未执行
        else:
            logger.debug(f"任务 {self.task_id} 立即执行，跳过时间范围检查")
        
        # 5. 如果mode或interaction_note_count已更新，重新初始化agent以确保使用最新参数
        if hasattr(self, 'agent') and self.agent is not None:
            # 检查agent的mode是否需要更新
            if hasattr(self.agent, 'mode') and self.agent.mode != self.mode:
                logger.info(f"任务 {self.task_id} agent模式已更新，重新初始化agent")
                self.agent = self._init_agent(**self.context.get_xhs_params())
            elif hasattr(self.agent, 'interaction_note_count') and self.agent.interaction_note_count != self.interaction_note_count:
                logger.info(f"任务 {self.task_id} agent互动笔记数量已更新，重新初始化agent")
                self.agent = self._init_agent(**self.context.get_xhs_params())
        
        # 6. 执行任务
        # 绑定 task_id 和 bindtype 到 logger，使得所有日志都会被收集到 TaskLogCollector
        task_logger = logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG)
        task_logger.info(f"任务 {self.task_id} 第 {self.round_num} 轮次开始执行")
        
        try:
            # 4.1 检查mcp服务是否正常运行
            self._mcp_service_check()
            
            # 4.2 将用户专属cookies.json文件复制到MCP服务目录
            from app.data.constants import COOKIE_SOURCE_PATH
            
            user_cookies_file = os.path.join(
                get_user_cookies_path(self.xhs_account_id), 
                "cookies.json"
            )
            task_logger.debug(f"用户专属cookie地址: {user_cookies_file}")
            
            try:
                # 尝试部署账号cookies到MCP服务目录（xhs_mcp/cookies.json）
                self._dispatch_cookies(
                    source_path=user_cookies_file,
                    destination_path=COOKIE_SOURCE_PATH
                )
            except RuntimeError as e:
                task_logger.warning(
                    f"无法找到该账户cookies储备，删除当前cookies，准备重新登陆，错误: {e}"
                )
                self._clear_cookies()
            
            # 4.3 检查登录状态（在任务执行前）
            try:
                await self.agent.ensure_connected()
                login_status_info = await self.agent.check_login_status()
                is_logged_in = login_status_info.get("is_logged_in", False)
                
                # 更新 TaskInfo 的登录状态
                self.task_info.login_status = is_logged_in
                self.task_info.login_status_checked_at = datetime.datetime.now()
                
                # 保存到 context.meta 中
                self.context.update_meta(
                    login_status=is_logged_in,
                    login_status_checked_at=datetime.datetime.now().isoformat()
                )
                
                task_logger.info(f"登录状态检查完成: {'已登录' if is_logged_in else '未登录'}")
            except Exception as e:
                task_logger.warning(f"检查登录状态失败: {e}，继续执行任务")
                # 登录状态检查失败不影响任务执行
            
            # 4.4 运行agent任务
            # 注意：agent.run() 内部的日志不会自动包含 task_id
            # 如果需要收集 agent 内部日志，需要在 agent 初始化时传入 task_logger
            try:
                await self.agent.run()
            except Exception as e:
                task_logger.warning(f"agent任务执行失败，错误：{e}")
                # 即使agent执行失败，也继续执行收尾工作
            
            # 4.4 任务执行完成后，进行收尾工作
            try:
                self._close_task()
            except Exception as e:
                task_logger.error(f"任务收尾工作失败: {e}")
            
            # 4.5 更新执行轮次
            self.round_num += 1
            
            task_logger.info(f"任务 {self.task_id} 第 {self.round_num-1} 轮次执行完成")
            
            return True  # 返回True表示任务未到期，可以继续调度
            
        except Exception as e:
            task_logger.error(f"任务 {self.task_id} 执行过程中发生异常: {e}", exc_info=True)
            # 即使发生异常，如果任务未到期，仍然可以继续调度
            return datetime.date.today() < self.task_end_time

if __name__ == '__main__':
    task_test = TaskManager(
    sys_type=SYS_TYPE.MAC_INTEL.value,
    task_type=DEFAULT_TASK_TYPE.XHS_TYPE,
    xhs_account_id='start',
    xhs_account_name='start',
    user_query='start',
    user_topic='start',
    user_style='start',
    user_target_audience='start',
    task_id=None
    )
    task_test.run()