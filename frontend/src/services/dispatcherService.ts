import api from './api';
import type { DispatcherStatus, APIResponse } from '@/types/dispatcher';

export const dispatcherService = {
  // 获取调度器状态
  getStatus: async (): Promise<DispatcherStatus> =>
    api.get<DispatcherStatus>('/dispatcher/status') as unknown as Promise<DispatcherStatus>,

  // 启动调度器
  start: async (): Promise<APIResponse> =>
    api.post<APIResponse>('/dispatcher/start') as unknown as Promise<APIResponse>,

  // 停止调度器
  stop: async (): Promise<APIResponse> =>
    api.post<APIResponse>('/dispatcher/stop') as unknown as Promise<APIResponse>,
};
