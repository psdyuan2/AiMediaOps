import React, { useState, useEffect, useRef } from 'react';
import { Card, Typography, Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

const { Text } = Typography;

type BackendStatus = 'starting' | 'ready' | 'running' | 'timeout' | 'error' | 'stopped';

interface StartupCardProps {
  onReady?: () => void;
}

// 声明 Electron API 类型
declare global {
  interface Window {
    electronAPI?: {
      checkBackendHealth: () => Promise<boolean>;
      getLogContent: (logType: 'bootstrap' | 'backend') => Promise<string>;
      onBackendStatus: (callback: (status: string) => void) => () => void;
      onBootstrapLog: (callback: (log: string) => void) => () => void;
      onBackendLog: (callback: (log: string) => void) => () => void;
    };
  }
}

export const StartupCard: React.FC<StartupCardProps> = ({ onReady }) => {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('starting');
  const [logs, setLogs] = useState<string>('');
  const [isVisible, setIsVisible] = useState(true);
  const logContainerRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    // 只在 Electron 环境中运行
    if (!window.electronAPI) {
      console.log('Not in Electron environment, skipping startup card');
      setIsVisible(false);
      onReady?.();
      return;
    }

    const api = window.electronAPI;

    // 获取初始日志内容
    (async () => {
      try {
        const bootstrapLog = await api.getLogContent('bootstrap');
        const backendLog = await api.getLogContent('backend');
        setLogs((bootstrapLog + '\n' + backendLog).trim());
      } catch (error) {
        console.error('Failed to get initial logs:', error);
      }
    })();

    // 监听后端状态
    const unlistenStatus = api.onBackendStatus((status) => {
      const statusValue = status as BackendStatus;
      setBackendStatus(statusValue);
      
      if (statusValue === 'ready' || statusValue === 'running') {
        // 延迟隐藏卡片，让用户看到成功消息
        setTimeout(() => {
          setIsVisible(false);
          onReady?.();
        }, 1000);
      }
    });

    // 监听 bootstrap 日志
    const unlistenBootstrap = api.onBootstrapLog((log) => {
      if (log) {
        setLogs((prev) => {
          const newLogs = (prev + log).slice(-20000); // 保留最后 20000 字符
          return newLogs;
        });
      }
    });

    // 监听后端日志
    const unlistenBackend = api.onBackendLog((log) => {
      if (log) {
        setLogs((prev) => {
          const newLogs = (prev + log).slice(-20000); // 保留最后 20000 字符
          return newLogs;
        });
      }
    });

    // 清理函数
    return () => {
      unlistenStatus();
      unlistenBootstrap();
      unlistenBackend();
    };
  }, [onReady]);

  // 自动滚动到底部
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  if (!isVisible) {
    return null;
  }

  const getStatusText = () => {
    switch (backendStatus) {
      case 'starting':
        return '正在启动后端服务...';
      case 'ready':
        return '后端服务已就绪 ✓';
      case 'running':
        return '后端服务运行中 ✓';
      case 'timeout':
        return '后端服务启动超时 ⚠️';
      case 'error':
        return '后端服务启动失败 ❌';
      case 'stopped':
        return '后端服务已停止';
      default:
        return '初始化中...';
    }
  };

  const getStatusColor = () => {
    switch (backendStatus) {
      case 'ready':
      case 'running':
        return '#52c41a';
      case 'timeout':
      case 'error':
        return '#ff4d4f';
      default:
        return '#1890ff';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.45)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24
      }}
    >
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Spin
              indicator={<LoadingOutlined style={{ fontSize: 18 }} spin />}
              spinning={backendStatus === 'starting'}
            />
            <span>MoKe 正在启动</span>
          </div>
        }
        style={{ width: 'min(900px, 100%)', maxHeight: '80vh' }}
        styles={{ body: { padding: 16 } }}
      >
        <div style={{ marginBottom: 16 }}>
          <Text strong style={{ color: getStatusColor() }}>
            {getStatusText()}
          </Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            日志位置: ~/.moke/logs/bootstrap.log / backend.log
          </Text>
        </div>
        <pre
          ref={logContainerRef}
          style={{
            margin: 0,
            padding: 12,
            background: '#0b1220',
            color: '#cfe3ff',
            borderRadius: 8,
            fontSize: 12,
            fontFamily: 'Monaco, "Courier New", monospace',
            maxHeight: '60vh',
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            lineHeight: 1.5
          }}
        >
          {logs || '等待日志输出...'}
        </pre>
        {backendStatus === 'timeout' && (
          <div style={{ marginTop: 16, padding: 12, background: '#fff7e6', borderRadius: 4 }}>
            <Text type="warning">
              后端服务启动超时，请检查日志或重启应用。如果问题持续，请查看 ~/.moke/logs/ 目录下的日志文件。
            </Text>
          </div>
        )}
        {backendStatus === 'error' && (
          <div style={{ marginTop: 16, padding: 12, background: '#fff1f0', borderRadius: 4 }}>
            <Text type="danger">
              后端服务启动失败，请查看上方日志了解详情。
            </Text>
          </div>
        )}
      </Card>
    </div>
  );
};
