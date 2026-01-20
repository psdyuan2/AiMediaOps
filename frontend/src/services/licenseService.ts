import api from './api';

export interface LicenseStatus {
  success: boolean;
  activated: boolean;
  expired: boolean;
  config: {
    end_time?: string;
    task_num?: number;
    is_free?: boolean;
    price?: number;
  } | null;
  remaining_tasks: number;
  current_tasks: number;
  max_tasks: number; // 最大任务数（未激活为1，已激活为task_num）
  is_free_trial: boolean; // 是否为免费试用
}

export interface ActivateResponse {
  success: boolean;
  message: string;
  config?: LicenseStatus['config'];
}

// 获取激活状态
export const getLicenseStatus = async (): Promise<LicenseStatus> => {
  // GET /api/v1/license/status
  const response = await api.get<LicenseStatus>('/license/status');
  return response;
};

// 激活注册码
export const activateLicense = async (licenseCode: string): Promise<ActivateResponse> => {
  // POST /api/v1/license/activate
  const response = await api.post<ActivateResponse>('/license/activate', {
    license_code: licenseCode,
  });
  return response;
};

