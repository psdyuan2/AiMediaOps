import React, { useState } from 'react';
import { Card, Badge, Button, Space, Tag, Popconfirm, Tooltip } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  LoginOutlined,
  FileTextOutlined,
  FolderOutlined,
  PlayCircleOutlined,
  PauseOutlined,
  CaretDownOutlined,
  CaretUpOutlined,
  StarOutlined,
  MessageOutlined,
  SendOutlined,
} from '@ant-design/icons';
import type { Task, TaskMode } from '@/types/task';
import { useTaskStore } from '@/store/taskStore';
import { useLicenseStore } from '@/store/licenseStore';
import { formatDateTime, getStatusColor, getStatusText } from '@/utils/format';

interface TaskCardProps {
  task: Task;
  onEdit: (task: Task) => void;
  onLogin: (task: Task) => void;
  onViewLogs: (task: Task) => void;
  onViewResources: (task: Task) => void;
}

const getModeIcon = (mode: TaskMode) => {
  switch (mode) {
    case 'standard':
      return <StarOutlined style={{ color: '#1890ff' }} />;
    case 'interaction':
      return <MessageOutlined style={{ color: '#52c41a' }} />;
    case 'publish':
      return <SendOutlined style={{ color: '#faad14' }} />;
    default:
      return null;
  }
};

const getModeLabel = (mode: TaskMode) => {
  switch (mode) {
    case 'standard':
      return '标准模式：互动 + 发布';
    case 'interaction':
      return '互动模式：仅互动';
    case 'publish':
      return '发布模式：仅发布';
    default:
      return '';
  }
};

export const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onEdit,
  onLogin,
  onViewLogs,
  onViewResources,
}) => {
  const [expanded, setExpanded] = useState(false);
  const { deleteTask, pauseTask, resumeTask, executeTask, selectTask } = useTaskStore();
   const { licenseStatus } = useLicenseStore();
   const canExecuteImmediately = licenseStatus?.activated ?? false;

  const handleDelete = async () => {
    await deleteTask(task.task_id);
  };

  const handlePause = async () => {
    await pauseTask(task.task_id);
  };

  const handleResume = async () => {
    await resumeTask(task.task_id);
  };

  const handleExecute = async () => {
    await executeTask(task.task_id);
  };

  const handleSelect = () => {
    selectTask(task);
  };

  return (
    <Card
      hoverable
      style={{ marginBottom: 16 }}
      onClick={handleSelect}
      className={useTaskStore.getState().selectedTask?.task_id === task.task_id ? 'selected-task' : ''}
      styles={{
        body: { padding: '16px' },
      }}
    >
      {/* 卡片头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
              {task.account_name || task.account_id}
            </div>
            <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
              账号ID: {task.account_id}
            </div>
            <Space size="small">
              <Badge status={getStatusColor(task.status)} text={getStatusText(task.status)} />
              {task.login_status !== null && task.login_status !== undefined && (
                <Tag color={task.login_status ? 'green' : 'red'}>
                  {task.login_status ? '✓ 已登录' : '✗ 未登录'}
                </Tag>
              )}
            </Space>
          </div>
        </div>

        <Space>
          {task.mode && (
            <Tooltip title={getModeLabel(task.mode)}>
              <span style={{ 
                display: 'inline-flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                width: 24,
                height: 24,
                cursor: 'default'
              }}>
                {getModeIcon(task.mode)}
              </span>
            </Tooltip>
          )}
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              onEdit(task);
            }}
            title="编辑"
          />
          <Popconfirm
            title="确定要删除这个任务吗？"
            onConfirm={(e) => {
              e?.stopPropagation();
              handleDelete();
            }}
            onCancel={(e) => e?.stopPropagation()}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
              title="删除"
            />
          </Popconfirm>
          <Button
            type="text"
            icon={expanded ? <CaretUpOutlined /> : <CaretDownOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            title={expanded ? '收起' : '展开'}
          />
        </Space>
      </div>

          {/* 卡片内容（可展开） */}
      {expanded && (
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
          <div style={{ marginBottom: 16 }}>
            <Space orientation="vertical" size="small" style={{ width: '100%' }}>
              <div>
                <span style={{ color: '#999' }}>下次执行: </span>
                <span>{formatDateTime(task.next_execution_time)}</span>
              </div>
              <div>
                <span style={{ color: '#999' }}>执行轮次: </span>
                <span>{task.round_num || 0}</span>
              </div>
              {task.last_execution_time && (
                <div>
                  <span style={{ color: '#999' }}>上次执行: </span>
                  <span>{formatDateTime(task.last_execution_time)}</span>
                </div>
              )}
            </Space>
          </div>

          {/* 操作按钮组 */}
          <Space wrap>
            {task.status !== 'completed' && task.status !== 'running' && (
              <Tooltip
                title={
                  canExecuteImmediately
                    ? '立即执行任务'
                    : '免费试用版不支持立即执行，请激活产品以使用此功能'
                }
              >
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                  disabled={!canExecuteImmediately}
                onClick={(e) => {
                  e.stopPropagation();
                  handleExecute();
                }}
              >
                立即执行
              </Button>
              </Tooltip>
            )}
            {task.status === 'paused' ? (
              <Button
                icon={<PlayCircleOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleResume();
                }}
              >
                恢复
              </Button>
            ) : (
              (task.status === 'pending' || task.status === 'running') && (
                <Button
                  icon={<PauseOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePause();
                  }}
                >
                  暂停
                </Button>
              )
            )}
            <Button
              icon={<LoginOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onLogin(task);
              }}
            >
              登录
            </Button>
            <Button
              icon={<FolderOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onViewResources(task);
              }}
            >
              资源
            </Button>
            <Button
              icon={<FileTextOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onViewLogs(task);
              }}
            >
              日志
            </Button>
          </Space>
        </div>
      )}
    </Card>
  );
};
