import axios from 'axios';
import type { AxiosInstance } from 'axios';
import { message } from 'antd';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

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

// 响应拦截器
api.interceptors.response.use(
  <T = any>(response: any): T => {
    // 直接返回 response.data，这样调用方可以直接使用数据
    return response.data as T;
  },
  (error) => {
    // 统一错误处理
    const errorMessage = error.response?.data?.detail || error.message || '请求失败';
    
    // 对于长时间运行的请求（如执行任务），不显示错误提示
    if (error.config?.timeout && error.config.timeout > 60000) {
      // 长时间运行的请求，错误信息由调用方处理
      return Promise.reject(error);
    }
    
    message.error(errorMessage);
    return Promise.reject(error);
  }
);

export default api;
