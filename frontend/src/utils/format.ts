import dayjs from 'dayjs';

export const formatDateTime = (dateTimeStr: string | null | undefined): string => {
  if (!dateTimeStr) return '-';
  return dayjs(dateTimeStr).format('YYYY-MM-DD HH:mm:ss');
};

export const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-';
  return dayjs(dateStr).format('YYYY-MM-DD');
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export const getStatusColor = (status: string): 'default' | 'processing' | 'warning' | 'success' | 'error' => {
  const colorMap: Record<string, 'default' | 'processing' | 'warning' | 'success' | 'error'> = {
    pending: 'default',
    running: 'processing',
    paused: 'warning',
    completed: 'success',
    error: 'error',
  };
  return colorMap[status] || 'default';
};

export const getStatusText = (status: string): string => {
  const textMap: Record<string, string> = {
    pending: '等待执行',
    running: '运行中',
    paused: '已暂停',
    completed: '已完成',
    error: '错误',
  };
  return textMap[status] || status;
};
