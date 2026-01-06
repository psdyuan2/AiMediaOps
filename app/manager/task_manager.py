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
            self.task_type = kwargs.get('task_type', DEFAULT_TASK_TYPE.XHS_TYPE)
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
            self.valid_time_range = kwargs.get('valid_time_rage', [8, 22])
            self.round_num = 0
            # 初始化context
            self.context = Task_Manager_Context(self.task_id)
            self.context.create_new_meta(**kwargs)
        else:
            # 传入task_id, 通过历史缓存构建task
            # 初始化context
            self.context = Task_Manager_Context(self.task_id)
            self.context.create_from_meta()
            # 从context中获取该参数
            self.task_type = self.context.get('task_type')
            self.task_end_time = self.context.get('task_end_time')
            self.interval = self.context.get('interval')
            self.valid_time_range = self.context.get('valid_time_range')
            self.round_num = self.context.get('round_num')
        # 初始化暂停开关变量
        self.data_path = Path(__file__).resolve()
        switch_path = Path.joinpath(self.data_path.parent, f"{self.task_id}_task_switch/")
        self.task_switch = Cache(str(switch_path))
        self.task_resume()
        # 初始化小红书
        self.agent = self._init_agent(**self.context.get_xhs_params())

    def _init_agent(self, **kwargs):
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
                mcp_server_url="http://localhost:18060/mcp"  # 默认值
            )

            logger.info(f"小红书智能体初始化成功: user_id={self.xhs_account_id}, task_id={self.task_id}")
            return agent
        else:
            logger.warning(f"未知的任务类型: {self.task_type}")
            return None
    def task_pause(self):
        self.task_switch.set('state', 'PAUSE')
    def task_resume(self):
        self.task_switch.set('state', 'RUNNING')
    def _mcp_service_check(self):
        #
        # 注意：SYS_TYPE现在是Enum，需要使用.value获取字符串值
        if self.sys_type == SYS_TYPE.MAC_INTEL.value:
            pass
        pass

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
        2. 确保用户的cookies文件被更新
        """
        # 1. 构建路径
        source_file = os.path.join(COOKIE_TARGET_PATH, "cookies.json")
        user_cookies_dir = get_user_cookies_path(self.xhs_account_id)
        target_file = os.path.join(user_cookies_dir, "cookies.json")

        # 2. 验证源文件
        if not os.path.exists(source_file):
            logger.warning(f"MCP目录中cookies.json不存在: {source_file}，跳过反向复制")
            return

        if not os.path.isfile(source_file):
            logger.warning(f"MCP目录中cookies.json不是文件: {source_file}，跳过反向复制")
            return

        # 3. 确保目标目录存在
        os.makedirs(user_cookies_dir, exist_ok=True)

        # 4. 复制文件
        try:
            shutil.copy2(source_file, target_file)
            logger.info(f"cookies反向复制完成: {source_file} -> {target_file}")
        except Exception as e:
            logger.error(f"cookies反向复制失败: {e}")
            # 因为是收尾工作，只记录错误不抛出异常

    def _check_time_valid(self):
        """
        判断小时数是否在范围内（仅限同日，不处理跨夜）。

        Args:
            time_range: [开始小时, 结束小时], e.g., [9, 18]
            target_hour: 待判断的小时数，默认当前时间
        """
        target_hour = datetime.datetime.now().hour
        start, end = self.valid_time_range[0], self.valid_time_range[1]

        # Python 特有的链式比较，等同于 start <= target_hour and target_hour <= end
        return start <= target_hour <= end
    async def run(self):
        while datetime.date.today() < self.task_end_time:
            # 任务运行条件检查
            # 1.检查任务是否是暂停状态：
            if self.task_switch.get('state') == 'PAUSE':
                logger.warning(f"任务{self.task_id} 第 {self.round_num} 任务暂停")
                time.sleep(5)
                continue
            # 2.检查任务是否在执行时间区间：
            if not self._check_time_valid():
                logger.warning(f"任务{self.task_id} 第 {self.round_num} 次任务未执行，不在执行时间范围内")
                time.sleep(5)
                continue
            logger.info(f"任务 {self.task_id} 第 {self.round_num}")
            # 检查mcp服务是否正常运行
            self._mcp_service_check()
            # 将用户专属cookies.json文件复制到MCP服务目录
            user_cookies_file = os.path.join(get_user_cookies_path(self.xhs_account_id), "cookies.json")
            logger.debug(f"用户专属cookie地址: {user_cookies_file}")

            try:
                # 尝试部署账号cookies
                self._dispatch_cookies(source_path=user_cookies_file,
                                   destination_path=COOKIE_TARGET_PATH)
            except RuntimeError as e:
                logger.warning(f"无法找到该账户cookies储备，删除当前cookies，准备重新登陆，错误: {e}")
                self._clear_cookies()
            # 运行agent任务
            try:
                await self.agent.run()
            except Exception as e:
                logger.warning(f"agent任务执行失败，错误：{e}")
            # 任务执行完成后，进行收尾工作
            try:
                self._close_task()
            except Exception as e:
                logger.error(f"任务收尾工作失败: {e}")
            time.sleep(self.interval)

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