import uuid
from app.data.constants import SYS_TYPE, DEFAULT_TASK_TYPE, COOKIE_TARGET_PATH, DEFAULT_KNOWLEDGE_PATH
from app.agents.xiaohongshu.agent import XiaohongshuAgent
from app.core.llm import LLMService
from app.core.context import Context
from app.core.logger import logger
from app.utils.path_utils import *


class TaskManager:
    def __init__(self, sys_type, **kwargs):
        """
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
        """
        self.task_id = kwargs.get('task_id') or str(uuid.uuid4())
        self.sys_type = sys_type
        self.task_type = kwargs.get('task_type', DEFAULT_TASK_TYPE.XHS_TYPE)

        # 保存小红书相关参数
        self.xhs_account_id = kwargs.get('xhs_account_id')
        self.xhs_account_name = kwargs.get('xhs_account_name')
        self.user_query = kwargs.get('user_query')
        self.user_topic = kwargs.get('user_topic')
        self.user_style = kwargs.get('user_style')
        self.user_target_audience = kwargs.get('user_target_audience')

        self.agent = self._init_agent(**kwargs)
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

    def _mcp_service_check(self):
        # 检查 XHS_MCP_SERVICE_URL 状态，如果未运行，根据系统类型运行服务
        # 注意：SYS_TYPE现在是Enum，需要使用.value获取字符串值
        if self.sys_type == SYS_TYPE.MAC_INTEL.value:
            pass
        pass

    def _dispatch_cookies(self, source_path, destination_path):
        # 将cookies文件从source_path复制到destination_path并覆盖原有的cookies.json
        pass

    def _close_task(self):
        # 任务执行完成后的一系列操作
        ## 需要将
    def run(self):
        # 检查mcp服务是否正常运行
        self._mcp_service_check()
        # 将self.user_id对应的cookie复制到目标文件下，替换原有的cookie文件，并将原有cookie更换为
        self._dispatch_cookies(source_path=get_user_cookies_path(self.xhs_account_id),
                               destination_path=COOKIE_TARGET_PATH)
        # TODO: 实现任务执行逻辑
        pass
