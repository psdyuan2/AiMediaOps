import React, { useEffect, useState, useRef } from 'react';
import { Modal, Button, Space, Select, Input, Tag, Spin } from 'antd';
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import { taskService } from '@/services/taskService';
import type { Task, LogEntry } from '@/types/task';
import dayjs from 'dayjs';

interface LogViewerProps {
  open: boolean;
  task: Task | null;
  onCancel: () => void;
}

export const LogViewer: React.FC<LogViewerProps> = ({
  open,
  task,
  onCancel,
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [searchText, setSearchText] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && task) {
      loadLogs();
    } else {
      setLogs([]);
      setAutoRefresh(false);
    }
  }, [open, task]);

  useEffect(() => {
    if (autoRefresh && task) {
      const interval = setInterval(loadLogs, 3000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, task]);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const loadLogs = async () => {
    if (!task) return;
    
    setLoading(true);
    try {
      const params: any = { limit: 1000 };
      if (levelFilter) {
        params.level = levelFilter;
      }
      const response = await taskService.getTaskLogs(task.task_id, params);
      setLogs(response.logs || []);
    } catch (error: any) {
      console.error('加载日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const getLevelColor = (level: string): string => {
    const colorMap: Record<string, string> = {
      DEBUG: 'default',
      INFO: 'blue',
      WARNING: 'orange',
      ERROR: 'red',
      CRITICAL: 'red',
    };
    return colorMap[level.toUpperCase()] || 'default';
  };

  const filteredLogs = logs.filter((log) => {
    if (searchText) {
      return log.message.toLowerCase().includes(searchText.toLowerCase());
    }
    return true;
  });

  const downloadLogs = () => {
    if (!task) return;
    const content = filteredLogs.map(log => 
      `[${log.timestamp}] [${log.level}] ${log.message}`
    ).join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `task_${task.task_id}_logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!task) return null;

  return (
    <Modal
      title={`任务日志 - ${task.account_name || task.account_id}`}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={900}
      styles={{
        body: { padding: 0 },
      }}
    >
      <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={loadLogs} loading={loading}>
            刷新
          </Button>
          <Button
            type={autoRefresh ? 'primary' : 'default'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? '停止自动刷新' : '自动刷新'}
          </Button>
          <Button
            type={autoScroll ? 'primary' : 'default'}
            onClick={() => setAutoScroll(!autoScroll)}
          >
            {autoScroll ? '自动滚动' : '停止滚动'}
          </Button>
          <Select
            style={{ width: 120 }}
            placeholder="日志级别"
            value={levelFilter || undefined}
            onChange={setLevelFilter}
            allowClear
          >
            <Select.Option value="DEBUG">DEBUG</Select.Option>
            <Select.Option value="INFO">INFO</Select.Option>
            <Select.Option value="WARNING">WARNING</Select.Option>
            <Select.Option value="ERROR">ERROR</Select.Option>
            <Select.Option value="CRITICAL">CRITICAL</Select.Option>
          </Select>
          <Input
            placeholder="搜索日志..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
          <Button icon={<DownloadOutlined />} onClick={downloadLogs}>
            下载日志
          </Button>
        </Space>
      </div>

      <div
        ref={logContainerRef}
        style={{
          height: '500px',
          overflow: 'auto',
          padding: '16px',
          background: '#1e1e1e',
          color: '#d4d4d4',
          fontFamily: 'monospace',
          fontSize: '12px',
        }}
      >
        <Spin spinning={loading}>
          {filteredLogs.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
              暂无日志
            </div>
          ) : (
            filteredLogs.map((log, index) => (
              <div key={index} style={{ marginBottom: 8, lineHeight: '1.5' }}>
                <span style={{ color: '#858585' }}>
                  [{dayjs(log.timestamp).format('HH:mm:ss')}]
                </span>
                <Tag color={getLevelColor(log.level)} style={{ margin: '0 8px' }}>
                  {log.level}
                </Tag>
                <span>{log.message}</span>
              </div>
            ))
          )}
        </Spin>
      </div>

      <div style={{ padding: '8px 16px', borderTop: '1px solid #f0f0f0', fontSize: '12px', color: '#999' }}>
        共 {filteredLogs.length} 条日志（显示 {logs.length} 条）
      </div>
    </Modal>
  );
};
