import React, { useEffect } from 'react';
import { Card, Empty, Spin, Select, Space, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { TaskCard } from '../TaskCard';
import { useTaskStore } from '@/store/taskStore';
import type { Task } from '@/types/task';

interface TaskListProps {
  onEdit: (task: Task) => void;
  onLogin: (task: Task) => void;
  onViewLogs: (task: Task) => void;
  onViewResources: (task: Task) => void;
}

export const TaskList: React.FC<TaskListProps> = ({
  onEdit,
  onLogin,
  onViewLogs,
  onViewResources,
}) => {
  const { tasks, loading, fetchTasks } = useTaskStore();
  const [statusFilter, setStatusFilter] = React.useState<string>('');
  const [accountFilter, setAccountFilter] = React.useState<string>('');

  useEffect(() => {
    fetchTasks();
    // 每10秒刷新一次
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  // 获取所有账户ID（去重）
  const accountIds = Array.from(new Set(tasks.map(t => t.account_id)));

  // 过滤任务
  const filteredTasks = tasks.filter((task) => {
    if (statusFilter && task.status !== statusFilter) return false;
    if (accountFilter && task.account_id !== accountFilter) return false;
    return true;
  });

  return (
    <Card
      title="任务列表"
      extra={
        <Space>
          <Select
            style={{ width: 120 }}
            placeholder="全部状态"
            value={statusFilter || undefined}
            onChange={setStatusFilter}
            allowClear
          >
            <Select.Option value="pending">等待执行</Select.Option>
            <Select.Option value="running">运行中</Select.Option>
            <Select.Option value="paused">已暂停</Select.Option>
            <Select.Option value="completed">已完成</Select.Option>
            <Select.Option value="error">错误</Select.Option>
          </Select>
          <Select
            style={{ width: 150 }}
            placeholder="全部账户"
            value={accountFilter || undefined}
            onChange={setAccountFilter}
            allowClear
          >
            {accountIds.map((accountId) => (
              <Select.Option key={accountId} value={accountId}>
                {accountId}
              </Select.Option>
            ))}
          </Select>
          <Button icon={<ReloadOutlined />} onClick={fetchTasks} loading={loading}>
            刷新
          </Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        {filteredTasks.length === 0 ? (
          <Empty description={loading ? '加载中...' : '暂无任务'} />
        ) : (
          <div>
            {filteredTasks.map((task) => (
              <TaskCard
                key={task.task_id}
                task={task}
                onEdit={onEdit}
                onLogin={onLogin}
                onViewLogs={onViewLogs}
                onViewResources={onViewResources}
              />
            ))}
          </div>
        )}
      </Spin>
    </Card>
  );
};
