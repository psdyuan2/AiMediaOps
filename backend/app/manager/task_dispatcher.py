"""
任务调度器模块

负责管理多个任务的调度执行，确保所有任务串行执行（避免cookie冲突），
并根据每个任务的执行时间配置进行智能调度。
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime as dt, date, timedelta
from pathlib import Path

from app.core.logger import logger
from app.manager.task_manager import TaskManager
from app.manager.task_info import TaskInfo, TaskStatus
from app.data.constants import SYS_TYPE, DEFAULT_TASK_TYPE
from app.core.config import APP_DATA_DIR


class TaskDispatcher:
    """任务调度器"""
    
    def __init__(self, dispatcher_dir: Optional[str] = None):
        """
        初始化调度器
        
        初始化：
        - execution_lock: 全局执行锁
        - all_tasks: 任务注册表
        - account_tasks: 账户任务映射
        - running_task: 当前运行的任务
        - scheduler_task: 调度器主循环任务
        - _stop_event: 停止事件
        - _dispatcher_dir: 持久化目录
        - _config_file: 配置文件路径
        
        Args:
            dispatcher_dir: 持久化目录路径，默认为 APP_DATA_DIR/dispatcher/
        """
        self.execution_lock = asyncio.Lock()
        self.all_tasks: Dict[str, TaskInfo] = {}
        self.account_tasks: Dict[str, List[str]] = {}  # account_id -> [task_id, ...]
        self.running_task: Optional[TaskInfo] = None
        self.scheduler_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # 初始化持久化目录
        if dispatcher_dir is None:
            self._dispatcher_dir = APP_DATA_DIR / "dispatcher"
        else:
            self._dispatcher_dir = Path(dispatcher_dir)
        
        # 确保目录存在
        os.makedirs(self._dispatcher_dir, exist_ok=True)
        
        # 配置文件路径
        self._config_file = os.path.join(self._dispatcher_dir, "dispatch_config.json")
        
        # 加载历史任务
        self._load_state()
    
    async def add_task(self, sys_type: str, **kwargs) -> str:
        """
        添加新任务
        
        Args:
            sys_type: 操作系统类型
            **kwargs: TaskManager 初始化参数
                - task_type: 任务类型（如 DEFAULT_TASK_TYPE.XHS_TYPE）
                - xhs_account_id: 小红书账户ID（必填，用于XHS_TYPE）
                - ... 其他 TaskManager 参数
            
        Returns:
            task_id: 新创建的任务ID
            
        Raises:
            ValueError: 如果账户ID已存在（同一任务类型下账户ID必须唯一）
        """
        # 1. 提取任务类型和账户ID
        # 注意：task_type 应该在接口层已经转换为枚举类型，这里只做验证
        task_type = kwargs.get('task_type', DEFAULT_TASK_TYPE.XHS_TYPE)
        
        # 验证 task_type 类型：应该是枚举类型
        if not isinstance(task_type, DEFAULT_TASK_TYPE):
            raise ValueError(f"task_type 必须是 DEFAULT_TASK_TYPE 枚举类型，当前类型: {type(task_type)}")
        
        account_id = None
        
        if task_type == DEFAULT_TASK_TYPE.XHS_TYPE:
            account_id = kwargs.get('xhs_account_id')
            if not account_id:
                raise ValueError("小红书任务必须提供 xhs_account_id 参数")
        else:
            raise ValueError(f"不支持的任务类型: {task_type}")
        
        # 2. 校验账户ID唯一性
        self._validate_account_uniqueness(task_type, account_id)
        
        # 3. 创建 TaskManager 实例
        task_manager = TaskManager(sys_type=sys_type, **kwargs)
        task_id = task_manager.task_id
        
        # 4. 创建 TaskInfo 对象
        # 获取模式，如果没有则使用默认值
        from app.data.constants import TaskMode
        mode_str = kwargs.get('mode', TaskMode.STANDARD.value)
        if isinstance(mode_str, TaskMode):
            mode = mode_str
        elif isinstance(mode_str, str):
            try:
                mode = TaskMode(mode_str)
            except ValueError:
                logger.warning(f"无效的模式值: {mode_str}，使用默认值 {TaskMode.STANDARD.value}")
                mode = TaskMode.STANDARD
        else:
            mode = TaskMode.STANDARD
        
        # 获取互动笔记数量，默认3，限制在1-5之间
        interaction_note_count = kwargs.get('interaction_note_count', 3)
        interaction_note_count = max(1, min(5, int(interaction_note_count))) if interaction_note_count else 3
        
        task_info = TaskInfo(
            task_id=task_id,
            account_id=account_id,
            account_name=kwargs.get('xhs_account_name', ''),
            task_type=task_type.value,  # 保存枚举的字符串值
            task_manager=task_manager,
            status=TaskStatus.PENDING,
            interval=task_manager.interval,
            valid_time_range=task_manager.valid_time_range,
            task_end_time=task_manager.task_end_time,
            mode=mode,
            interaction_note_count=interaction_note_count,
            kwargs=kwargs
        )
        
        # 5. 计算首次执行时间
        task_info.next_execution_time = self._calculate_next_execution_time(task_info)
        
        # 6. 更新任务注册表
        self.all_tasks[task_id] = task_info
        
        if account_id not in self.account_tasks:
            self.account_tasks[account_id] = []
        self.account_tasks[account_id].append(task_id)
        
        logger.info(
            f"任务添加成功: task_id={task_id}, account_id={account_id}, "
            f"next_execution_time={task_info.next_execution_time}"
        )
        
        # 7. 保存状态
        self._save_state()
        
        # 8. 如果调度器未启动，触发重新计算（但不自动启动）
        if self.scheduler_task is None:
            logger.warning("调度器未启动，请调用 start() 方法启动调度器")
        
        return task_id
    
    def _validate_account_uniqueness(self, task_type: DEFAULT_TASK_TYPE, account_id: str):
        """
        校验账户ID唯一性
        
        规则：
        - 对于同一任务类型（如 XHS_TYPE），每个账户ID只能对应一个任务
        - 如果已存在相同任务类型和相同账户ID的任务，则拒绝创建新任务
        
        Args:
            task_type: 任务类型枚举（DEFAULT_TASK_TYPE）
            account_id: 账户ID（如 xhs_account_id）
            
        Raises:
            ValueError: 如果账户ID已存在，包含详细信息
        """
        if not isinstance(task_type, DEFAULT_TASK_TYPE):
            raise ValueError(f"task_type 必须是 DEFAULT_TASK_TYPE 枚举类型")
        
        task_type_value = task_type.value  # 枚举的字符串值
        
        # 检查该任务类型下是否已存在相同账户ID的任务
        for task_id, task_info in self.all_tasks.items():
            # task_info.task_type 在 TaskInfo 中保存的是字符串值，直接比较
            if task_info.task_type == task_type_value and task_info.account_id == account_id:
                raise ValueError(
                    f"账户ID '{account_id}' 已存在任务 '{task_id}'（状态: {task_info.status.value}），"
                    f"同一账户不能创建多个任务。请先删除或完成现有任务。"
                )
    
    def _calculate_next_execution_time(self, task_info: TaskInfo) -> Optional[dt]:
        """
        计算任务的下次执行时间
        
        规则：
        1. 基础时间 = last_execution_time + interval（如果 last_execution_time 存在）
        2. 如果基础时间是过去的时间，基于当前时间重新计算
        3. 如果基础时间不在 valid_time_range 内，调整到下一个有效时间段
        4. 如果超过 task_end_time，返回 None
        
        Args:
            task_info: 任务信息
            
        Returns:
            下次执行时间，如果任务已结束则返回 None
        """
        now = dt.now()
        
        if task_info.last_execution_time is None:
            # 首次执行，基于当前时间
            if self._is_in_valid_time_range(now, task_info.valid_time_range):
                return now
            else:
                return self._get_next_valid_time_start(now, task_info.valid_time_range)
        
        # 计算基础时间
        base_time = task_info.last_execution_time + timedelta(seconds=task_info.interval)
        
        # 如果基础时间是过去的时间，基于当前时间重新计算
        if base_time <= now:
            logger.debug(f"任务 {task_info.task_id} 计算的基础时间 {base_time} 是过去的时间，基于当前时间 {now} 重新计算")
            # 基于当前时间计算，确保在有效时间范围内
            if self._is_in_valid_time_range(now, task_info.valid_time_range):
                base_time = now
            else:
                base_time = self._get_next_valid_time_start(now, task_info.valid_time_range)
                # 如果计算出的时间还是过去，再次基于当前时间计算
                if base_time and base_time <= now:
                    # 基于当前时间 + interval 计算
                    base_time = now + timedelta(seconds=task_info.interval)
                    if not self._is_in_valid_time_range(base_time, task_info.valid_time_range):
                        base_time = self._get_next_valid_time_start(base_time, task_info.valid_time_range)
        
        # 检查是否超过结束时间（如果 task_end_time 为 None，则不检查）
        if task_info.task_end_time is not None and base_time and base_time.date() >= task_info.task_end_time:
            return None
        
        # 检查是否在有效时间范围内
        if base_time and self._is_in_valid_time_range(base_time, task_info.valid_time_range):
            return base_time
        else:
            # 调整到下一个有效时间段的开始
            if base_time:
                return self._get_next_valid_time_start(base_time, task_info.valid_time_range)
            else:
                return None
    
    def _is_in_valid_time_range(self, check_time: dt, valid_time_range: Optional[List[int]]) -> bool:
        """
        检查时间是否在有效时间范围内
        
        Args:
            check_time: 待检查的时间
            valid_time_range: 有效时间范围 [start_hour, end_hour]，或 None 表示无限制
            
        Returns:
            bool: 是否在有效时间范围内（None 时返回 True）
        """
        # None 表示无限制，直接返回 True
        if valid_time_range is None:
            return True
        
        # 确保 valid_time_range 有效
        if not isinstance(valid_time_range, list) or len(valid_time_range) < 2:
            logger.warning(f"valid_time_range 无效: {valid_time_range}，使用默认值 [8, 22]")
            valid_time_range = [8, 22]
        
        start_hour, end_hour = valid_time_range[0], valid_time_range[1]
        current_hour = check_time.hour
        return start_hour <= current_hour <= end_hour
    
    def _get_next_valid_time_start(self, base_time: dt, valid_time_range: Optional[List[int]]) -> Optional[dt]:
        """
        获取下一个有效时间段的开始时间
        
        Args:
            base_time: 基础时间
            valid_time_range: 有效时间范围 [start_hour, end_hour]，或 None 表示无限制
            
        Returns:
            下一个有效时间段的开始时间（None 时直接返回 base_time）
        """
        # None 表示无限制，直接返回 base_time
        if valid_time_range is None:
            return base_time
        
        # 确保 valid_time_range 有效
        if not isinstance(valid_time_range, list) or len(valid_time_range) < 2:
            logger.warning(f"valid_time_range 无效: {valid_time_range}，使用默认值 [8, 22]")
            valid_time_range = [8, 22]
        
        start_hour, end_hour = valid_time_range[0], valid_time_range[1]
        current_hour = base_time.hour
        
        if current_hour < start_hour:
            # 当天还未到开始时间，返回当天的开始时间
            return base_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        elif current_hour > end_hour:
            # 当天已超过结束时间，返回次日的开始时间
            next_day = base_time + timedelta(days=1)
            return next_day.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        else:
            # 在有效时间范围内，返回次日的开始时间
            next_day = base_time + timedelta(days=1)
            return next_day.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    async def update_task(self, task_id: str, **update_data) -> bool:
        """
        更新任务属性
        
        Args:
            task_id: 任务ID
            **update_data: 要更新的字段，支持：
                - user_query, user_topic, user_style, user_target_audience
                - task_end_time (date 或 ISO 格式字符串)
                - interval (int, 秒)
                - valid_time_range (List[int], [start_hour, end_hour])
        
        Returns:
            bool: 是否更新成功
        """
        if task_id not in self.all_tasks:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        task_info = self.all_tasks[task_id]
        task_manager = task_info.task_manager
        
        # 检查任务状态：运行中的任务允许更新，但属性在下一次执行时生效
        if task_info.status == TaskStatus.RUNNING:
            logger.info(f"任务 {task_id} 正在运行，属性将在下一次执行时生效")
        
        try:
            # 1. 更新 Task_Manager_Context.meta
            context = task_manager.context
            meta_updates = {}
            
            # 处理内容相关属性
            if 'user_query' in update_data and update_data['user_query'] is not None:
                meta_updates['user_query'] = update_data['user_query']
                task_manager.user_query = update_data['user_query']
            
            if 'user_topic' in update_data and update_data['user_topic'] is not None:
                meta_updates['user_topic'] = update_data['user_topic']
                task_manager.user_topic = update_data['user_topic']
            
            if 'user_style' in update_data and update_data['user_style'] is not None:
                meta_updates['user_style'] = update_data['user_style']
                task_manager.user_style = update_data['user_style']
            
            if 'user_target_audience' in update_data and update_data['user_target_audience'] is not None:
                meta_updates['user_target_audience'] = update_data['user_target_audience']
                task_manager.user_target_audience = update_data['user_target_audience']
            
            # 处理调度相关属性
            need_recalculate_time = False
            
            if 'interval' in update_data and update_data['interval'] is not None:
                interval = update_data['interval']
                if interval < 60:
                    raise ValueError(f"执行间隔不能小于60秒，当前值: {interval}")
                meta_updates['interval'] = interval
                task_info.interval = interval
                task_manager.interval = interval
                need_recalculate_time = True
            
            if 'valid_time_range' in update_data:
                valid_time_range = update_data['valid_time_range']
                # None 表示无限制
                if valid_time_range is None:
                    meta_updates['valid_time_range'] = None
                    task_info.valid_time_range = None
                    task_manager.valid_time_range = None
                    need_recalculate_time = True
                elif isinstance(valid_time_range, list) and len(valid_time_range) == 2:
                    if not (0 <= valid_time_range[0] < 24 and 0 <= valid_time_range[1] < 24):
                        raise ValueError(f"时间范围必须在 0-23 之间，当前值: {valid_time_range}")
                    if valid_time_range[0] >= valid_time_range[1]:
                        raise ValueError(f"开始时间必须小于结束时间，当前值: {valid_time_range}")
                    meta_updates['valid_time_range'] = valid_time_range
                    task_info.valid_time_range = valid_time_range
                    task_manager.valid_time_range = valid_time_range
                    need_recalculate_time = True
                else:
                    raise ValueError(f"有效时间范围必须是 [start_hour, end_hour] 格式或 None（无限制），当前值: {valid_time_range}")
            
            if 'task_end_time' in update_data and update_data['task_end_time'] is not None:
                task_end_time = update_data['task_end_time']
                # 处理日期格式
                if isinstance(task_end_time, str):
                    try:
                        task_end_time = date.fromisoformat(task_end_time)
                    except ValueError:
                        raise ValueError(f"任务结束时间格式错误，应为 ISO 日期格式 (YYYY-MM-DD)，当前值: {task_end_time}")
                elif not isinstance(task_end_time, date):
                    raise ValueError(f"任务结束时间必须是 date 对象或 ISO 日期字符串，当前类型: {type(task_end_time)}")
                
                meta_updates['task_end_time'] = task_end_time.isoformat()
                task_info.task_end_time = task_end_time
                task_manager.task_end_time = task_end_time
                need_recalculate_time = True
            
            # 处理模式更新
            if 'mode' in update_data and update_data['mode'] is not None:
                from app.data.constants import TaskMode
                mode_str = update_data['mode']
                if isinstance(mode_str, str):
                    try:
                        mode = TaskMode(mode_str)
                    except ValueError:
                        raise ValueError(f"无效的模式值: {mode_str}，有效值: {[m.value for m in TaskMode]}")
                elif isinstance(mode_str, TaskMode):
                    mode = mode_str
                else:
                    raise ValueError(f"模式必须是字符串或 TaskMode 枚举，当前类型: {type(mode_str)}")
                
                meta_updates['mode'] = mode.value
                task_info.mode = mode
                task_info.kwargs['mode'] = mode.value
            
            # 处理互动笔记数量更新
            if 'interaction_note_count' in update_data and update_data['interaction_note_count'] is not None:
                interaction_note_count = update_data['interaction_note_count']
                if not isinstance(interaction_note_count, int) or interaction_note_count < 1 or interaction_note_count > 5:
                    raise ValueError(f"互动笔记数量必须在 1-5 之间，当前值: {interaction_note_count}")
                
                meta_updates['interaction_note_count'] = interaction_note_count
                task_info.interaction_note_count = interaction_note_count
                task_info.kwargs['interaction_note_count'] = interaction_note_count
            
            # 更新 context.meta
            if meta_updates:
                context.update_meta(**meta_updates)
            
            # 2. 更新 TaskInfo.kwargs（用于恢复任务时使用）
            if 'user_query' in update_data:
                task_info.kwargs['user_query'] = update_data['user_query']
            if 'user_topic' in update_data:
                task_info.kwargs['user_topic'] = update_data['user_topic']
            if 'user_style' in update_data:
                task_info.kwargs['user_style'] = update_data['user_style']
            if 'user_target_audience' in update_data:
                task_info.kwargs['user_target_audience'] = update_data['user_target_audience']
            if 'interval' in update_data and update_data['interval'] is not None:
                task_info.kwargs['interval'] = update_data['interval']
            if 'valid_time_range' in update_data and update_data['valid_time_range'] is not None:
                task_info.kwargs['valid_time_range'] = update_data['valid_time_range']
            if 'task_end_time' in update_data and update_data['task_end_time'] is not None:
                if isinstance(task_info.task_end_time, date):
                    task_info.kwargs['task_end_time'] = task_info.task_end_time.isoformat()
                else:
                    task_info.kwargs['task_end_time'] = task_info.task_end_time
            if 'mode' in update_data and update_data['mode'] is not None:
                # mode 已经在上面处理并更新到 task_info.mode，这里同步到 kwargs
                task_info.kwargs['mode'] = task_info.mode.value if hasattr(task_info.mode, 'value') else str(task_info.mode)
            if 'interaction_note_count' in update_data and update_data['interaction_note_count'] is not None:
                # interaction_note_count 已经在上面处理并更新到 task_info.interaction_note_count，这里同步到 kwargs
                task_info.kwargs['interaction_note_count'] = task_info.interaction_note_count
            
            # 3. 如果修改了调度相关属性，重新计算 next_execution_time
            if need_recalculate_time:
                # 检查任务是否已到期
                if task_info.task_end_time is not None and dt.now().date() >= task_info.task_end_time:
                    task_info.update_next_execution_time(None)
                    if task_info.status == TaskStatus.PENDING:
                        task_info.update_status(TaskStatus.COMPLETED)
                    logger.info(f"任务 {task_id} 已到期，更新状态为 COMPLETED")
                else:
                    # 重新计算下次执行时间
                    next_time = self._calculate_next_execution_time(task_info)
                    task_info.update_next_execution_time(next_time)
                    logger.info(f"任务 {task_id} 的下次执行时间已重新计算: {next_time}")
            
            # 4. 更新 updated_at
            task_info.updated_at = dt.now()
            
            # 5. 保存状态
            self._save_state()
            
            logger.info(f"任务 {task_id} 属性更新成功: {list(meta_updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"更新任务 {task_id} 失败: {e}", exc_info=True)
            raise
    
    async def remove_task(self, task_id: str) -> bool:
        """
        删除任务（如果任务正在运行，先等待完成再删除）
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否删除成功
        """
        if task_id not in self.all_tasks:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        task_info = self.all_tasks[task_id]
        
        # 如果任务正在运行，先暂停
        if task_info.status == TaskStatus.RUNNING:
            logger.info(f"任务 {task_id} 正在运行，先暂停再删除")
            self.pause_task(task_id)
            # 等待任务完成（这里简化处理，实际可能需要更复杂的等待逻辑）
            await asyncio.sleep(1)
        
        # 从注册表中删除
        account_id = task_info.account_id
        if account_id in self.account_tasks:
            if task_id in self.account_tasks[account_id]:
                self.account_tasks[account_id].remove(task_id)
            if not self.account_tasks[account_id]:
                del self.account_tasks[account_id]
        
        del self.all_tasks[task_id]
        
        # 保存状态
        self._save_state()
        
        logger.info(f"任务删除成功: {task_id}")
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否暂停成功
        """
        if task_id not in self.all_tasks:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        task_info = self.all_tasks[task_id]
        
        # 调用 TaskManager 的暂停方法
        task_info.task_manager.task_pause()
        
        # 设置 next_execution_time 为 None（暂停调度）
        task_info.update_next_execution_time(None)
        task_info.update_status(TaskStatus.PAUSED)
        
        # 保存状态
        self._save_state()
        
        logger.info(f"任务暂停成功: {task_id}")
        return True
    
    def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否恢复成功
        """
        if task_id not in self.all_tasks:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        task_info = self.all_tasks[task_id]
        
        if task_info.status != TaskStatus.PAUSED:
            logger.warning(f"任务不是暂停状态，无法恢复: {task_id}, status={task_info.status}")
            return False
        
        # 调用 TaskManager 的恢复方法
        task_info.task_manager.task_resume()
        
        # 重新计算 next_execution_time
        next_time = self._calculate_next_execution_time(task_info)
        task_info.update_next_execution_time(next_time)
        task_info.update_status(TaskStatus.PENDING)
        
        # 保存状态
        self._save_state()
        
        logger.info(f"任务恢复成功: {task_id}, next_execution_time={next_time}")
        return True
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            TaskInfo: 任务信息，如果不存在返回 None
        """
        return self.all_tasks.get(task_id)
    
    def list_tasks(self, account_id: Optional[str] = None) -> List[TaskInfo]:
        """
        列出所有任务
        
        Args:
            account_id: 可选，如果指定则只返回该账户的任务
            
        Returns:
            List[TaskInfo]: 任务列表（按 next_execution_time 排序）
        """
        if account_id:
            task_ids = self.account_tasks.get(account_id, [])
            tasks = [self.all_tasks[tid] for tid in task_ids if tid in self.all_tasks]
        else:
            tasks = list(self.all_tasks.values())
        
        # 按 next_execution_time 排序（None 排在最后）
        tasks.sort(key=lambda x: (
            x.next_execution_time if x.next_execution_time else dt.max,
            x.created_at
        ))
        
        return tasks
    
    def reorder_task(self, task_id: str, priority_offset: int) -> bool:
        """
        调整任务的执行优先级（通过修改 next_execution_time）
        
        Args:
            task_id: 任务ID
            priority_offset: 优先级偏移量（秒）
                - 正数：延后执行（如 3600 表示延后1小时）
                - 负数：提前执行（如 -1800 表示提前30分钟）
            
        Returns:
            bool: 是否调整成功
            
        Raises:
            ValueError: 如果任务不存在、正在运行、已暂停或已结束
        """
        if task_id not in self.all_tasks:
            raise ValueError(f"任务不存在: {task_id}")
        
        task_info = self.all_tasks[task_id]
        
        if task_info.status == TaskStatus.RUNNING:
            raise ValueError(f"任务正在运行，无法调整优先级: {task_id}")
        
        if task_info.status == TaskStatus.PAUSED:
            raise ValueError(f"任务已暂停，请先恢复任务: {task_id}")
        
        if task_info.status == TaskStatus.COMPLETED:
            raise ValueError(f"任务已完成，无法调整优先级: {task_id}")
        
        if task_info.next_execution_time is None:
            raise ValueError(f"任务没有下次执行时间，无法调整: {task_id}")
        
        # 调整 next_execution_time
        new_time = task_info.next_execution_time + timedelta(seconds=priority_offset)
        
        # 确保调整后的时间在有效时间范围内
        if not self._is_in_valid_time_range(new_time, task_info.valid_time_range):
            new_time = self._get_next_valid_time_start(new_time, task_info.valid_time_range)
        
        # 检查是否超过结束时间（如果设置了结束时间）
        if task_info.task_end_time is not None and new_time.date() >= task_info.task_end_time:
            raise ValueError(f"调整后的时间超过任务结束时间: {task_id}")
        
        task_info.update_next_execution_time(new_time)
        
        # 保存状态
        self._save_state()
        
        logger.info(f"任务优先级调整成功: {task_id}, new_next_execution_time={new_time}")
        
        return True
    
    async def execute_task_immediately(self, task_id: str, update_next_execution_time: bool = True) -> dict:
        """
        立即执行指定任务（不等待调度器调度）
        
        注意：此方法会等待任务执行完成，可能会花费较长时间（几分钟），请确保客户端设置了足够的超时时间。
        
        Args:
            task_id: 任务ID
            update_next_execution_time: 是否更新下次执行时间（默认为 True，基于当前时间重新计算）
            
        Returns:
            dict: 执行结果，包含执行状态、执行时间等信息
            
        Raises:
            ValueError: 如果任务不存在或状态不允许执行
            RuntimeError: 如果任务执行失败
        """
        # 1. 检查任务是否存在
        task_info = self.all_tasks.get(task_id)
        if not task_info:
            raise ValueError(f"任务不存在: {task_id}")
        
        # 2. 检查任务状态
        if task_info.status == TaskStatus.COMPLETED:
            raise ValueError(f"任务已完成，无法再次执行: {task_id}")
        
        # 3. 如果任务已暂停，给出警告但不阻止执行
        if task_info.status == TaskStatus.PAUSED:
            logger.warning(f"任务 {task_id} 当前状态为 PAUSED，但仍将立即执行")
        
        # 4. 检查是否有其他任务正在运行（需要使用全局锁检查）
        # 注意：这里只是初步检查，真正的检查在获取锁之后进行
        if self.running_task and self.running_task.task_id != task_id:
            raise ValueError(
                f"当前有其他任务正在执行中（task_id: {self.running_task.task_id}），"
                f"无法立即执行任务 {task_id}。请等待当前任务完成后再试。"
            )
        
        # 5. 如果任务正在运行，检查是否是同一个任务
        if task_info.status == TaskStatus.RUNNING:
            if self.running_task and self.running_task.task_id == task_id:
                raise ValueError(f"任务正在执行中，无法重复执行: {task_id}")
            else:
                # 状态不一致，更新状态
                logger.warning(f"任务 {task_id} 状态为 RUNNING 但不在运行列表中，将重置状态")
                task_info.update_status(TaskStatus.PENDING)
        
        # 6. 使用全局锁执行任务（确保同一时间只有一个任务执行）
        async with self.execution_lock:
            # 再次检查是否有其他任务正在运行（可能在获取锁的过程中有其他任务开始执行）
            if self.running_task and self.running_task.task_id != task_id:
                raise ValueError(
                    f"当前有其他任务正在执行中（task_id: {self.running_task.task_id}），"
                    f"无法立即执行任务 {task_id}。请等待当前任务完成后再试。"
                )
            # 再次检查任务状态（可能在获取锁的过程中被修改）
            if task_info.status == TaskStatus.COMPLETED:
                raise ValueError(f"任务已完成，无法再次执行: {task_id}")
            
            try:
                # 标记为运行中
                task_info.update_status(TaskStatus.RUNNING)
                self.running_task = task_info
                
                # 绑定 task_id 和 bindtype 到 logger，使得调度器级别的日志也被收集
                from app.data.constants import LogBindType
                task_logger = logger.bind(task_id=task_id, bindtype=LogBindType.TASK_LOG)
                
                execution_start_time = dt.now()
                task_logger.info(
                    f"立即执行任务: task_id={task_info.task_id}, "
                    f"account_id={task_info.account_id}"
                )
                
                # 执行任务（同步执行，等待完成）
                # TaskManager.run_once() 内部已经绑定了 task_id，所以任务执行日志会被收集
                # 立即执行时跳过时间范围检查（skip_time_check=True）
                should_continue = await task_info.task_manager.run_once(skip_time_check=True)
                
                # 更新执行时间
                execution_end_time = dt.now()
                task_info.update_execution_time(execution_end_time)
                
                execution_result = {
                    "task_id": task_id,
                    "execution_start_time": execution_start_time.isoformat(),
                    "execution_end_time": execution_end_time.isoformat(),
                    "duration_seconds": (execution_end_time - execution_start_time).total_seconds(),
                    "should_continue": should_continue,
                    "success": True
                }
                
                if should_continue:
                    # 任务未到期，可以继续
                    # 检查任务是否在执行过程中被暂停
                    if task_info.status == TaskStatus.PAUSED:
                        task_logger.info(
                            f"任务立即执行完成，但任务已被暂停: task_id={task_info.task_id}"
                        )
                        execution_result["next_execution_time"] = None
                    else:
                        if update_next_execution_time:
                            # 基于当前时间重新计算下次执行时间
                            next_time = self._calculate_next_execution_time(task_info)
                            task_info.update_next_execution_time(next_time)
                            execution_result["next_execution_time"] = next_time.isoformat() if next_time else None
                        
                        task_info.update_status(TaskStatus.PENDING)
                        task_logger.info(
                            f"任务立即执行完成: task_id={task_info.task_id}, "
                            f"next_execution_time={execution_result.get('next_execution_time', '未更新')}"
                        )
                else:
                    # 任务已到期
                    task_info.update_next_execution_time(None)
                    task_info.update_status(TaskStatus.COMPLETED)
                    execution_result["next_execution_time"] = None
                    task_logger.info(f"任务立即执行完成，但任务已到期: task_id={task_info.task_id}")
                
                # 保存状态
                self._save_state()
                
                return execution_result
            
            except Exception as e:
                task_logger.error(f"任务立即执行异常: task_id={task_info.task_id}, error={e}", exc_info=True)
                task_info.update_status(TaskStatus.ERROR)
                
                # 即使出错，如果任务未到期，仍然可以继续调度
                # 但需要检查任务是否在执行过程中被暂停
                if task_info.status != TaskStatus.PAUSED and (task_info.task_end_time is None or dt.now().date() < task_info.task_end_time):
                    if update_next_execution_time:
                        next_time = self._calculate_next_execution_time(task_info)
                        task_info.update_next_execution_time(next_time)
                    task_info.update_status(TaskStatus.PENDING)
                
                # 保存状态
                self._save_state()
                
                # 返回错误信息
                raise RuntimeError(f"任务执行失败: {str(e)}")
            
            finally:
                # 清除运行中标记
                if self.running_task and self.running_task.task_id == task_id:
                    self.running_task = None
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        logger.info("调度器主循环启动")
        
        while not self._stop_event.is_set():
            try:
                now = dt.now()
                
                # 1. 找到所有需要执行的任务（next_execution_time <= now 且状态为 PENDING）
                ready_tasks = [
                    task_info for task_info in self.all_tasks.values()
                    if (task_info.next_execution_time is not None and 
                        task_info.next_execution_time <= now and
                        task_info.status == TaskStatus.PENDING)
                ]
                
                # 如果找到了待执行的任务，记录日志
                if ready_tasks:
                    logger.info(f"找到 {len(ready_tasks)} 个待执行任务: {[t.task_id for t in ready_tasks]}")
                else:
                    # 记录所有任务的状态，用于调试
                    for task_info in self.all_tasks.values():
                        logger.debug(
                            f"任务 {task_info.task_id}: status={task_info.status.value}, "
                            f"next_execution_time={task_info.next_execution_time}, "
                            f"now={now}, ready={task_info.next_execution_time <= now if task_info.next_execution_time else False}"
                        )
                
                # 2. 按 next_execution_time 排序（时间冲突时按创建时间排序）
                ready_tasks.sort(key=lambda x: (x.next_execution_time, x.created_at))
                
                # 3. 执行任务
                for task_info in ready_tasks:
                    if self._stop_event.is_set():
                        break
                    
                    # 再次检查任务状态（可能在其他地方被修改）
                    if task_info.status != TaskStatus.PENDING:
                        continue
                    
                    # 使用全局锁串行执行
                    async with self.execution_lock:
                        if task_info.status != TaskStatus.PENDING:
                            continue
                        
                        try:
                            # 标记为运行中
                            task_info.update_status(TaskStatus.RUNNING)
                            self.running_task = task_info
                            
                            # 绑定 task_id 和 bindtype 到 logger，使得调度器级别的日志也被收集
                            from app.data.constants import LogBindType
                            task_logger = logger.bind(task_id=task_info.task_id, bindtype=LogBindType.TASK_LOG)
                            task_logger.info(
                                f"开始执行任务: task_id={task_info.task_id}, "
                                f"account_id={task_info.account_id}"
                            )
                            
                            # 执行任务（TaskManager.run_once() 内部已经绑定了 task_id）
                            should_continue = await task_info.task_manager.run_once()
                            
                            # 更新执行时间
                            task_info.update_execution_time(dt.now())
                            
                            if should_continue:
                                # 检查任务是否在执行过程中被暂停
                                # 如果状态已经是 PAUSED（在执行过程中被暂停），保持 PAUSED 状态
                                if task_info.status == TaskStatus.PAUSED:
                                    task_logger.info(
                                        f"任务执行完成，但任务已被暂停: task_id={task_info.task_id}"
                                    )
                                else:
                                    # 计算下次执行时间
                                    next_time = self._calculate_next_execution_time(task_info)
                                    task_info.update_next_execution_time(next_time)
                                    task_info.update_status(TaskStatus.PENDING)
                                    task_logger.info(
                                        f"任务执行完成: task_id={task_info.task_id}, "
                                        f"next_execution_time={next_time}"
                                    )
                            else:
                                # 任务已到期
                                task_info.update_next_execution_time(None)
                                task_info.update_status(TaskStatus.COMPLETED)
                                task_logger.info(f"任务已到期: task_id={task_info.task_id}")
                            
                            # 保存状态
                            self._save_state()
                        
                        except Exception as e:
                            task_logger.error(f"任务执行异常: task_id={task_info.task_id}, error={e}", exc_info=True)
                            task_info.update_status(TaskStatus.ERROR)
                            # 即使出错，如果任务未到期，仍然可以继续调度
                            # 检查任务是否未到期（如果 task_end_time 为 None，则认为任务未到期）
                            # 但需要检查任务是否在执行过程中被暂停
                            if task_info.status != TaskStatus.PAUSED and (task_info.task_end_time is None or dt.now().date() < task_info.task_end_time):
                                next_time = self._calculate_next_execution_time(task_info)
                                task_info.update_next_execution_time(next_time)
                                task_info.update_status(TaskStatus.PENDING)
                            
                            # 保存状态
                            self._save_state()
                        
                        finally:
                            self.running_task = None
                
                # 4. 计算下次检查时间
                pending_tasks = [
                    t for t in self.all_tasks.values()
                    if t.next_execution_time is not None and t.status == TaskStatus.PENDING
                ]
                
                if pending_tasks:
                    next_check_time = min(t.next_execution_time for t in pending_tasks)
                    wait_seconds = (next_check_time - dt.now()).total_seconds()
                    
                    if wait_seconds > 0:
                        # 等待到下次检查时间，但最多等待60秒
                        wait_seconds = min(wait_seconds, 60)
                        try:
                            await asyncio.wait_for(
                                self._stop_event.wait(),
                                timeout=wait_seconds
                            )
                        except asyncio.TimeoutError:
                            pass  # 正常超时，继续循环
                    else:
                        # 立即检查
                        await asyncio.sleep(0.1)
                else:
                    # 没有待执行任务，等待一段时间
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=60)
                    except asyncio.TimeoutError:
                        pass  # 正常超时，继续循环
            
            except Exception as e:
                logger.error(f"调度器循环异常: {e}", exc_info=True)
                await asyncio.sleep(5)
        
        logger.info("调度器主循环停止")
    
    async def start(self):
        """启动调度器（开始执行任务队列）"""
        if self.scheduler_task is not None and not self.scheduler_task.done():
            logger.warning("调度器已在运行")
            return
        
        self._stop_event.clear()
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("调度器已启动")
    
    async def stop(self):
        """停止调度器（等待当前任务完成，不再执行新任务）"""
        logger.info("正在停止调度器...")
        self._stop_event.set()
        
        if self.scheduler_task is not None:
            # 等待调度器循环结束
            try:
                await asyncio.wait_for(self.scheduler_task, timeout=30)
            except asyncio.TimeoutError:
                logger.warning("调度器停止超时，强制取消")
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
        
        # 等待当前运行的任务完成
        if self.running_task is not None:
            logger.info(f"等待当前任务完成: {self.running_task.task_id}")
            # 这里简化处理，实际可能需要更复杂的等待逻辑
            await asyncio.sleep(5)
        
        # 保存最终状态
        self._save_state()
        
        logger.info("调度器已停止")
    
    def _save_state(self):
        """
        保存调度器状态到本地文件
        
        保存的信息包括：
        - 所有任务的信息（不包括 task_manager 对象，保存创建参数）
        - 账户任务映射
        - 任务执行时间信息
        """
        try:
            # 递归函数：将字典中的 date 对象转换为字符串
            def serialize_dates(obj):
                """递归处理对象，将 date 和 datetime 对象转换为字符串"""
                if isinstance(obj, date):
                    return obj.isoformat()
                elif isinstance(obj, dt):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {key: serialize_dates(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_dates(item) for item in obj]
                elif isinstance(obj, (int, float, str, bool, type(None))):
                    return obj
                else:
                    # 其他类型尝试转换为字符串
                    return str(obj)
            
            # 构建可序列化的任务数据
            tasks_data = []
            for task_id, task_info in self.all_tasks.items():
                # 处理 kwargs，确保其中的 date 对象被序列化
                serialized_kwargs = serialize_dates(task_info.kwargs) if task_info.kwargs else {}
                
                task_data = {
                    "task_id": task_info.task_id,
                    "account_id": task_info.account_id,
                    "account_name": task_info.account_name,
                    "task_type": task_info.task_type,
                    "status": task_info.status.value,
                    "mode": task_info.mode.value if hasattr(task_info.mode, 'value') else str(task_info.mode),
                    "interaction_note_count": task_info.interaction_note_count,
                    "interval": task_info.interval,
                    "valid_time_range": task_info.valid_time_range,
                    "task_end_time": task_info.task_end_time.isoformat() if isinstance(task_info.task_end_time, date) else (None if task_info.task_end_time is None else str(task_info.task_end_time)),
                    "last_execution_time": task_info.last_execution_time.isoformat() if task_info.last_execution_time else None,
                    "next_execution_time": task_info.next_execution_time.isoformat() if task_info.next_execution_time else None,
                    "created_at": task_info.created_at.isoformat() if task_info.created_at else None,
                    "updated_at": task_info.updated_at.isoformat() if task_info.updated_at else None,
                    "round_num": getattr(task_info.task_manager, 'round_num', 0),  # 保存任务执行轮次
                    "kwargs": serialized_kwargs,  # 保存任务创建参数（已处理 date 对象），用于恢复 TaskManager
                    "sys_type": serialized_kwargs.get('sys_type', SYS_TYPE.MAC_INTEL.value) if serialized_kwargs else SYS_TYPE.MAC_INTEL.value  # 保存 sys_type
                }
                tasks_data.append(task_data)
            
            # 构建配置数据
            config_data = {
                "version": "1.0",
                "saved_at": dt.now().isoformat(),
                "tasks": tasks_data,
                "account_tasks": self.account_tasks
            }
            
            # 保存到文件
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"调度器状态已保存: {self._config_file}")
        
        except Exception as e:
            logger.error(f"保存调度器状态失败: {e}", exc_info=True)
    
    def _load_state(self):
        """
        从本地文件加载调度器状态
        
        恢复所有任务信息，并重新创建 TaskManager 实例
        """
        if not os.path.exists(self._config_file):
            logger.info(f"调度器配置文件不存在，使用空状态: {self._config_file}")
            return
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 恢复账户任务映射
            self.account_tasks = config_data.get("account_tasks", {})
            
            # 恢复任务信息
            tasks_data = config_data.get("tasks", [])
            loaded_count = 0
            
            for task_data in tasks_data:
                try:
                    # 提取任务参数
                    # 检查必需字段是否存在
                    if "task_id" not in task_data:
                        logger.error(f"任务数据缺少 task_id 字段，跳过该任务。数据: {task_data}")
                        continue
                    
                    task_id = task_data["task_id"]
                    sys_type = task_data.get("sys_type", SYS_TYPE.MAC_INTEL.value)
                    kwargs = task_data.get("kwargs", {})
                    
                    # 确保 task_id 在 kwargs 中（用于恢复 TaskManager）
                    kwargs['task_id'] = task_id
                    
                    # 从配置文件恢复时，task_type 可能是字符串、枚举对象或 None，需要转换为枚举
                    task_type_str = kwargs.get('task_type', 'xhs_type')
                    if task_type_str is None:
                        kwargs['task_type'] = DEFAULT_TASK_TYPE.XHS_TYPE
                    elif isinstance(task_type_str, str):
                        # 处理字符串值或枚举对象的字符串表示
                        if task_type_str == 'xhs_type' or task_type_str == DEFAULT_TASK_TYPE.XHS_TYPE.value or 'XHS_TYPE' in str(task_type_str):
                            kwargs['task_type'] = DEFAULT_TASK_TYPE.XHS_TYPE
                        else:
                            logger.warning(f"恢复任务时遇到不支持的任务类型: {task_type_str}，使用默认值")
                            kwargs['task_type'] = DEFAULT_TASK_TYPE.XHS_TYPE
                    # 如果已经是枚举类型，保持不变
                    elif isinstance(task_type_str, DEFAULT_TASK_TYPE):
                        kwargs['task_type'] = task_type_str
                    else:
                        logger.warning(f"恢复任务时 task_type 类型不正确: {type(task_type_str)}，使用默认值")
                        kwargs['task_type'] = DEFAULT_TASK_TYPE.XHS_TYPE  # 默认值
                    
                    # 重新创建 TaskManager 实例（此时 task_type 已经是枚举类型）
                    task_manager = TaskManager(sys_type=sys_type, **kwargs)
                    
                    # 恢复 task_end_time，处理 None 值和字符串 "None"
                    task_end_time_value = task_data.get("task_end_time")
                    if task_end_time_value is None or task_end_time_value == "None":
                        # 如果为 None，使用默认值（30天后）
                        restored_task_end_time = date.today() + timedelta(days=30)
                        logger.warning(f"任务 {task_id} 的 task_end_time 为 None，使用默认值: {restored_task_end_time}")
                    elif isinstance(task_end_time_value, str):
                        try:
                            restored_task_end_time = date.fromisoformat(task_end_time_value)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"无法解析任务 {task_id} 的 task_end_time: {task_end_time_value}，使用默认值，错误: {e}")
                            restored_task_end_time = date.today() + timedelta(days=30)
                    elif isinstance(task_end_time_value, date):
                        restored_task_end_time = task_end_time_value
                    else:
                        logger.warning(f"任务 {task_id} 的 task_end_time 类型不正确: {type(task_end_time_value)}，使用默认值")
                        restored_task_end_time = date.today() + timedelta(days=30)
                    
                    # 恢复 TaskInfo
                    # 从 context.meta 中恢复登录状态
                    login_status = None
                    login_status_checked_at = None
                    if task_manager and hasattr(task_manager, 'context') and task_manager.context is not None:
                        try:
                            # context.meta 是字典，直接访问
                            if hasattr(task_manager.context, 'meta'):
                                meta = task_manager.context.meta
                                if meta and isinstance(meta, dict):
                                    login_status = meta.get('login_status')
                                    if login_status is not None:
                                        login_status = bool(login_status)
                                    login_status_checked_at_str = meta.get('login_status_checked_at')
                                    if login_status_checked_at_str:
                                        try:
                                            login_status_checked_at = dt.fromisoformat(login_status_checked_at_str)
                                        except (ValueError, TypeError):
                                            pass
                        except Exception as e:
                            logger.warning(f"恢复任务 {task_id} 的登录状态失败: {e}，使用默认值")
                            # 继续执行，使用默认值 None
                    
                    # 恢复模式，如果不存在则使用默认值
                    from app.data.constants import TaskMode
                    mode_str = task_data.get("mode", TaskMode.STANDARD.value)
                    try:
                        restored_mode = TaskMode(mode_str) if isinstance(mode_str, str) else (mode_str if isinstance(mode_str, TaskMode) else TaskMode.STANDARD)
                    except (ValueError, TypeError):
                        logger.warning(f"任务 {task_id} 的模式值无效: {mode_str}，使用默认值 {TaskMode.STANDARD.value}")
                        restored_mode = TaskMode.STANDARD
                    
                    # 恢复互动笔记数量，默认3，限制在1-5之间
                    interaction_note_count = task_data.get("interaction_note_count", 3)
                    interaction_note_count = max(1, min(5, int(interaction_note_count))) if interaction_note_count else 3
                    
                    task_info = TaskInfo(
                        task_id=task_id,
                        account_id=task_data["account_id"],
                        account_name=task_data.get("account_name", ""),
                        task_type=task_data["task_type"],
                        task_manager=task_manager,
                        interval=task_data["interval"],
                        valid_time_range=task_data["valid_time_range"],
                        task_end_time=restored_task_end_time,
                        mode=restored_mode,
                        interaction_note_count=interaction_note_count,
                        kwargs=kwargs,
                        login_status=login_status,
                        login_status_checked_at=login_status_checked_at
                    )
                    
                    # 恢复状态和时间信息
                    restored_status = TaskStatus(task_data["status"])
                    
                    # 重要：如果任务状态是 RUNNING，说明服务重启前任务正在执行
                    # 但服务重启后，之前的执行进程已不存在，应该重置为 PENDING 状态
                    if restored_status == TaskStatus.RUNNING:
                        logger.warning(f"任务 {task_id} 恢复时状态为 RUNNING（可能是服务重启），重置为 PENDING")
                        task_info.status = TaskStatus.PENDING
                    else:
                        task_info.status = restored_status
                    
                    if task_data.get("last_execution_time"):
                        task_info.last_execution_time = dt.fromisoformat(task_data["last_execution_time"])
                    if task_data.get("next_execution_time"):
                        task_info.next_execution_time = dt.fromisoformat(task_data["next_execution_time"])
                    if task_data.get("created_at"):
                        task_info.created_at = dt.fromisoformat(task_data["created_at"])
                    if task_data.get("updated_at"):
                        task_info.updated_at = dt.fromisoformat(task_data["updated_at"])
                    
                    # 恢复 round_num（任务执行轮次）
                    if task_data.get("round_num") is not None:
                        task_manager.round_num = task_data["round_num"]
                    
                    # 如果 next_execution_time 是过去的时间且任务状态是 PENDING，重新计算下次执行时间
                    if task_info.status == TaskStatus.PENDING:
                        if task_info.next_execution_time is None:
                            # 如果没有下次执行时间，计算一个
                            next_time = self._calculate_next_execution_time(task_info)
                            if next_time:
                                task_info.update_next_execution_time(next_time)
                                logger.info(f"任务 {task_id} 恢复时没有下次执行时间，已计算: {next_time}")
                        elif task_info.next_execution_time < dt.now():
                            # 如果下次执行时间是过去的时间，重新计算
                            logger.info(f"任务 {task_id} 恢复时 next_execution_time ({task_info.next_execution_time}) 是过去的时间，重新计算")
                            next_time = self._calculate_next_execution_time(task_info)
                            if next_time:
                                task_info.update_next_execution_time(next_time)
                                logger.info(f"任务 {task_id} 下次执行时间已更新为: {next_time}")
                    
                    # 添加到任务注册表
                    self.all_tasks[task_id] = task_info
                    loaded_count += 1
                    
                    logger.info(f"任务恢复成功: task_id={task_id}, status={task_info.status.value}, next_execution_time={task_info.next_execution_time}")
                
                except KeyError as e:
                    # 处理缺少必需字段的情况
                    missing_key = str(e).strip("'\"")
                    logger.error(f"恢复任务失败: 缺少必需字段 '{missing_key}'，任务数据: {task_data}", exc_info=True)
                    continue
                except Exception as e:
                    task_id = task_data.get('task_id', 'unknown')
                    logger.error(f"恢复任务失败: task_id={task_id}, error={e}", exc_info=True)
                    continue
            
            logger.info(f"调度器状态加载完成: 共恢复 {loaded_count}/{len(tasks_data)} 个任务")
        
        except Exception as e:
            logger.error(f"加载调度器状态失败: {e}", exc_info=True)

