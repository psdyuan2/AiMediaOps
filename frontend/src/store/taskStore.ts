import { create } from 'zustand';
import { taskService } from '@/services/taskService';
import type { Task, TaskCreateRequest, TaskUpdateRequest } from '@/types/task';
import { message } from 'antd';

interface TaskStore {
  tasks: Task[];
  loading: boolean;
  error: string | null;
  selectedTask: Task | null;

  // Actions
  fetchTasks: () => Promise<void>;
  createTask: (data: TaskCreateRequest) => Promise<void>;
  updateTask: (taskId: string, data: TaskUpdateRequest) => Promise<void>;
  deleteTask: (taskId: string) => Promise<void>;
  pauseTask: (taskId: string) => Promise<void>;
  resumeTask: (taskId: string) => Promise<void>;
  executeTask: (taskId: string) => Promise<void>;
  selectTask: (task: Task | null) => void;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  loading: false,
  error: null,
  selectedTask: null,

  fetchTasks: async () => {
    set({ loading: true, error: null });
    try {
      const response = await taskService.getTasks({ limit: 1000 });
      set({ tasks: response.tasks, loading: false });
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '获取任务列表失败';
      set({ error: errorMsg, loading: false });
      message.error(errorMsg);
    }
  },

  createTask: async (data) => {
    try {
      await taskService.createTask(data);
      message.success('任务创建成功');
      await get().fetchTasks(); // 刷新列表
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '创建任务失败';
      set({ error: errorMsg });
      message.error(errorMsg);
      throw error;
    }
  },

  updateTask: async (taskId, data) => {
    try {
      await taskService.updateTask(taskId, data);
      message.success('任务更新成功');
      await get().fetchTasks(); // 刷新列表
      // 如果更新的是选中的任务，也更新 selectedTask
      if (get().selectedTask?.task_id === taskId) {
        const updatedTask = get().tasks.find(t => t.task_id === taskId);
        if (updatedTask) {
          set({ selectedTask: updatedTask });
        }
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '更新任务失败';
      set({ error: errorMsg });
      message.error(errorMsg);
      throw error;
    }
  },

  deleteTask: async (taskId) => {
    try {
      await taskService.deleteTask(taskId);
      message.success('任务删除成功');
      // 如果删除的是选中的任务，清空选中
      if (get().selectedTask?.task_id === taskId) {
        set({ selectedTask: null });
      }
      await get().fetchTasks(); // 刷新列表
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '删除任务失败';
      set({ error: errorMsg });
      message.error(errorMsg);
      throw error;
    }
  },

  pauseTask: async (taskId) => {
    try {
      await taskService.pauseTask(taskId);
      message.success('任务已暂停');
      await get().fetchTasks();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '暂停任务失败';
      set({ error: errorMsg });
      message.error(errorMsg);
      throw error;
    }
  },

  resumeTask: async (taskId) => {
    try {
      await taskService.resumeTask(taskId);
      message.success('任务已恢复');
      await get().fetchTasks();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '恢复任务失败';
      set({ error: errorMsg });
      message.error(errorMsg);
      throw error;
    }
  },

  executeTask: async (taskId) => {
    try {
      message.loading({ content: '任务执行中，请稍候...', key: 'execute', duration: 0 });
      await taskService.executeTask(taskId);
      message.success({ content: '任务执行成功', key: 'execute' });
      await get().fetchTasks();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '执行任务失败';
      message.error({ content: errorMsg, key: 'execute' });
      set({ error: errorMsg });
      throw error;
    }
  },

  selectTask: (task) => {
    set({ selectedTask: task });
  },
}));
