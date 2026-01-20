import { create } from 'zustand';
import { message } from 'antd';
import { getLicenseStatus, activateLicense, type LicenseStatus } from '@/services/licenseService';

interface LicenseStore {
  licenseStatus: LicenseStatus | null;
  loading: boolean;
  error: string | null;

  fetchLicenseStatus: () => Promise<void>;
  activate: (licenseCode: string) => Promise<boolean>;
}

export const useLicenseStore = create<LicenseStore>((set, get) => ({
  licenseStatus: null,
  loading: false,
  error: null,

  fetchLicenseStatus: async () => {
    set({ loading: true, error: null });
    try {
      const status = await getLicenseStatus();
      set({ licenseStatus: status, loading: false });
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || error.message || '获取激活状态失败';
      set({ error: errorMsg, loading: false });
      // 未激活或接口暂不可用时不强制提示，避免打扰用户
    }
  },

  activate: async (licenseCode: string) => {
    set({ loading: true, error: null });
    try {
      await activateLicense(licenseCode);
      message.success('激活成功！');
      await get().fetchLicenseStatus();
      return true;
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || error.message || '激活失败';
      set({ error: errorMsg, loading: false });
      message.error(errorMsg);
      return false;
    }
  },
}));

