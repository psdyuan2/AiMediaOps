import { create } from 'zustand';
import { dispatcherService } from '@/services/dispatcherService';
import type { DispatcherStatus } from '@/types/dispatcher';
import { message } from 'antd';

interface DispatcherStore {
  status: DispatcherStatus | null;
  loading: boolean;
  error: string | null;

  fetchStatus: () => Promise<void>;
  startDispatcher: () => Promise<void>;
  stopDispatcher: () => Promise<void>;
}

export const useDispatcherStore = create<DispatcherStore>((set, get) => ({
  status: null,
  loading: false,
  error: null,

  fetchStatus: async () => {
    set({ loading: true, error: null });
    try {
      const status = await dispatcherService.getStatus();
      set({ status, loading: false });
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '获取调度器状态失败';
      set({ error: errorMsg, loading: false });
      message.error(errorMsg);
    }
  },

  startDispatcher: async () => {
    try {
      await dispatcherService.start();
      message.success('调度器启动成功');
      await get().fetchStatus();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '启动调度器失败';
      set({ error: errorMsg });
      message.error(errorMsg);
      throw error;
    }
  },

  stopDispatcher: async () => {
    try {
      await dispatcherService.stop();
      message.success('调度器已停止');
      await get().fetchStatus();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '停止调度器失败';
      set({ error: errorMsg });
      message.error(errorMsg);
      throw error;
    }
  },
}));
