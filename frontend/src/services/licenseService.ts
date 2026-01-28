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
  // 添加时间戳防止缓存
  return api.get<LicenseStatus>(`/license/status?t=${Date.now()}`) as unknown as Promise<LicenseStatus>;
};

// 激活注册码
export const activateLicense = async (licenseCode: string): Promise<ActivateResponse> => {
  // POST /api/v1/license/activate
  return api.post<ActivateResponse>('/license/activate', {
    license_code: licenseCode,
  }) as unknown as Promise<ActivateResponse>;
};

