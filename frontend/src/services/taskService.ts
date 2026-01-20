import api from './api';
import type {
  Task,
  TaskListResponse,
  TaskCreateRequest,
  TaskUpdateRequest,
  TaskExecuteResponse,
  TaskLogsResponse,
  LoginQrcodeResponse,
  LoginStatusResponse,
  LoginConfirmResponse,
  ImagesListResponse,
  SourceFileResponse,
} from '@/types/task';
import type { APIResponse } from '@/types/dispatcher';

export const taskService = {
  // 获取任务列表
  getTasks: async (params?: { account_id?: string; status?: string; limit?: number; offset?: number }): Promise<TaskListResponse> =>
    api.get<TaskListResponse>('/tasks', { params }) as unknown as Promise<TaskListResponse>,

  // 获取任务详情
  getTask: async (taskId: string): Promise<Task> =>
    api.get<Task>(`/tasks/${taskId}`) as unknown as Promise<Task>,

  // 创建任务
  createTask: async (data: TaskCreateRequest): Promise<Task> =>
    api.post<Task>('/tasks', data) as unknown as Promise<Task>,

  // 更新任务
  updateTask: async (taskId: string, data: TaskUpdateRequest): Promise<Task> =>
    api.patch<Task>(`/tasks/${taskId}`, data) as unknown as Promise<Task>,

  // 删除任务
  deleteTask: async (taskId: string): Promise<APIResponse> =>
    api.delete<APIResponse>(`/tasks/${taskId}`) as unknown as Promise<APIResponse>,

  // 暂停任务
  pauseTask: async (taskId: string): Promise<APIResponse> =>
    api.post<APIResponse>(`/tasks/${taskId}/pause`) as unknown as Promise<APIResponse>,

  // 恢复任务
  resumeTask: async (taskId: string): Promise<APIResponse> =>
    api.post<APIResponse>(`/tasks/${taskId}/resume`) as unknown as Promise<APIResponse>,

  // 立即执行
  executeTask: async (taskId: string): Promise<TaskExecuteResponse> =>
    api.post<TaskExecuteResponse>(`/tasks/${taskId}/execute`, {}, { timeout: 1800000 }) as unknown as Promise<TaskExecuteResponse>, // 30 分钟超时

  // 获取任务日志
  getTaskLogs: async (taskId: string, params?: { since?: string; level?: string; limit?: number }): Promise<TaskLogsResponse> =>
    api.get<TaskLogsResponse>(`/tasks/${taskId}/logs`, { params }) as unknown as Promise<TaskLogsResponse>,

  // 获取登录二维码
  getLoginQrcode: async (taskId: string): Promise<LoginQrcodeResponse> =>
    api.get<LoginQrcodeResponse>(`/tasks/${taskId}/login/qrcode`) as unknown as Promise<LoginQrcodeResponse>,

  // 检查登录状态
  checkLoginStatus: async (taskId: string): Promise<LoginStatusResponse> =>
    api.get<LoginStatusResponse>(`/tasks/${taskId}/login/status`) as unknown as Promise<LoginStatusResponse>,

  // 确认登录
  confirmLogin: async (taskId: string): Promise<LoginConfirmResponse> =>
    api.post<LoginConfirmResponse>(`/tasks/${taskId}/login/confirm`) as unknown as Promise<LoginConfirmResponse>,

  // 获取任务图片列表
  getTaskImages: async (taskId: string): Promise<ImagesListResponse> =>
    api.get<ImagesListResponse>(`/tasks/${taskId}/resources/images`) as unknown as Promise<ImagesListResponse>,

  // 获取知识库文件
  getSourceFile: async (taskId: string): Promise<SourceFileResponse> =>
    api.get<SourceFileResponse>(`/tasks/${taskId}/resources/source`) as unknown as Promise<SourceFileResponse>,

  // 更新知识库文件
  updateSourceFile: async (taskId: string, content: string): Promise<APIResponse> =>
    api.put<APIResponse>(`/tasks/${taskId}/resources/source`, { content }) as unknown as Promise<APIResponse>,

  // 下载知识库文件
  downloadSourceFile: (taskId: string) => {
    const url = `${api.defaults.baseURL}/tasks/${taskId}/resources/source/download`;
    window.open(url, '_blank');
  },

  // 上传知识库文件
  uploadSourceFile: (taskId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<APIResponse>(`/tasks/${taskId}/resources/source/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};
