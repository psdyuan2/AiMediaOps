import axios from 'axios';
import type { AxiosInstance, AxiosError } from 'axios';
import { message, Modal } from 'antd';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8765/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 错误响应类型
interface ErrorResponse {
  success?: boolean;
  error?: string;
  error_code?: string;
  error_type?: string;
}

// 存储激活对话框打开函数（由组件注册）
let openActivateDialog: (() => void) | null = null;

// 对外导出注册函数，供 App / Layout 使用
export const registerActivateDialog = (fn: () => void) => {
  openActivateDialog = fn;
};

// 响应拦截器
api.interceptors.response.use(
  <T = any>(response: any): T => {
    // 直接返回 response.data，这样调用方可以直接使用数据
    return response.data as T;
  },
  (error: AxiosError<ErrorResponse>) => {
    const resp = error.response;
    const data = resp?.data;
    const statusCode = resp?.status;

    const rawMessage =
      data?.error || (data as any)?.detail || error.message || '请求失败';
    const errorCode = data?.error_code;
    const errorType = data?.error_type;
    const headers = resp?.headers || {};
    const licenseLimitHeader =
      (headers['x-license-limit'] as string | undefined) ??
      (headers['X-License-Limit'] as string | undefined);
    
    // 对于长时间运行的请求（如执行任务），不显示错误提示
    if (error.config?.timeout && error.config.timeout > 60000) {
      return Promise.reject(error);
    }
    
    // 处理与注册码相关的 403 限制（包含 error_type=license/task_limit 或头部标记为 free_trial）
    const isLicense403 =
      statusCode === 403 &&
      (errorType === 'license' ||
        errorType === 'task_limit' ||
        licenseLimitHeader === 'free_trial');

    if (isLicense403) {
      // 针对不同错误代码，给出更人性化的提示
      if (errorCode === 'LICENSE_NOT_ACTIVATED') {
        const uiMessage =
          '当前为免费试用版，仅支持创建 1 个任务，执行间隔固定为 2 小时，且不支持立即执行。\n' +
          '如需解锁完整功能，请使用激活码完成激活。';
        message.warning(uiMessage, 6);
        setTimeout(() => {
          if (openActivateDialog) {
            openActivateDialog();
          }
        }, 500);
      } else if (errorCode === 'LICENSE_EXPIRED') {
        const uiMessage =
          '您的套餐已到期，当前已退回免费试用模式（仅 1 个任务、2 小时间隔、不支持立即执行）。\n' +
          '请在“查看当前套餐”中续费或重新激活后再继续使用完整功能。';
        message.warning(uiMessage, 6);
        setTimeout(() => {
          if (openActivateDialog) {
            openActivateDialog();
          }
        }, 500);
      } else if (errorCode === 'TASK_LIMIT_REACHED') {
        // 任务数量限制，弹出对话框并引导查看套餐
        Modal.warning({
          title: '已达到当前套餐的任务上限',
          content:
            rawMessage +
            '\n\n你可以删除部分任务，或在“查看当前套餐”中升级套餐以创建更多任务。',
          okText: '查看当前套餐',
          onOk: () => {
            const event = new CustomEvent('openLicenseCard');
            window.dispatchEvent(event);
          },
        });
      } else if (licenseLimitHeader === 'free_trial') {
        // 免费版限制但没有明确错误代码（例如立即执行受限）
        const uiMessage =
          '当前为免费试用版，不支持此操作。\n' +
          '请在左侧“查看当前套餐”中使用激活码激活，以解锁完整功能。';
        message.warning(uiMessage, 6);
      } else {
        // 兜底：使用原始错误信息，但仍提示可以通过激活解决
        message.warning(
          `${rawMessage}\n\n如希望继续使用完整功能，请在“查看当前套餐”中完成激活。`,
          6,
        );
      }
    } else {
      // 其他错误统一使用 error 提示
      message.error(rawMessage);
    }

    return Promise.reject(error);
  },
);

export default api;
