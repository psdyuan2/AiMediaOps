const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 检查后端健康状态
  checkBackendHealth: () => ipcRenderer.invoke('check-backend-health'),
  
  // 获取日志内容
  getLogContent: (logType) => ipcRenderer.invoke('get-log-content', logType),
  
  // 监听后端状态变化
  onBackendStatus: (callback) => {
    ipcRenderer.on('backend-status', (event, status) => callback(status));
    return () => ipcRenderer.removeAllListeners('backend-status');
  },
  
  // 监听 bootstrap 日志
  onBootstrapLog: (callback) => {
    ipcRenderer.on('backend-bootstrap-log', (event, log) => callback(log));
    return () => ipcRenderer.removeAllListeners('backend-bootstrap-log');
  },
  
  // 监听后端日志
  onBackendLog: (callback) => {
    ipcRenderer.on('backend-log', (event, log) => callback(log));
    return () => ipcRenderer.removeAllListeners('backend-log');
  }
});
