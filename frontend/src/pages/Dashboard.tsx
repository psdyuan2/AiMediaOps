import React, { useState, useEffect } from 'react';
import { Card } from 'antd';
import { DispatcherControl } from '@/components/DispatcherControl';
import { TaskList } from '@/components/TaskList';
import { CreateTaskForm, EditTaskForm } from '@/components/TaskForm';
import { LoginDialog } from '@/components/LoginDialog';
import { LogViewer } from '@/components/LogViewer';
import { ResourceManager } from '@/components/ResourceManager';
import type { Task } from '@/types/task';
import { useTaskStore } from '@/store/taskStore';

export const Dashboard: React.FC = () => {
  const { } = useTaskStore();
  const [createTaskOpen, setCreateTaskOpen] = useState(false);
  const [editTaskOpen, setEditTaskOpen] = useState(false);
  const [loginDialogOpen, setLoginDialogOpen] = useState(false);
  const [logViewerOpen, setLogViewerOpen] = useState(false);
  const [resourceManagerOpen, setResourceManagerOpen] = useState(false);
  const [currentTask, setCurrentTask] = useState<Task | null>(null);

  // 监听创建任务事件（从 Sidebar 触发）
  useEffect(() => {
    const handleOpenCreateTask = () => {
      setCreateTaskOpen(true);
    };

    window.addEventListener('openCreateTaskDialog' as any, handleOpenCreateTask as EventListener);
    return () => {
      window.removeEventListener('openCreateTaskDialog' as any, handleOpenCreateTask as EventListener);
    };
  }, []);

  const handleEdit = (task: Task) => {
    setCurrentTask(task);
    setEditTaskOpen(true);
  };

  const handleLogin = (task: Task) => {
    setCurrentTask(task);
    setLoginDialogOpen(true);
  };

  const handleViewLogs = (task: Task) => {
    setCurrentTask(task);
    setLogViewerOpen(true);
  };

  const handleViewResources = (task: Task) => {
    setCurrentTask(task);
    setResourceManagerOpen(true);
  };

  const handleLoginSuccess = () => {
    useTaskStore.getState().fetchTasks();
  };

  return (
    <div>
      {/* 产品信息区域 */}
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'flex-start' }}>
          <div style={{ 
            textAlign: 'left'
          }}>
            <div style={{ marginBottom: 8, display: 'flex', alignItems: 'baseline', gap: 12 }}>
              <div style={{ fontSize: 22, fontWeight: 600, color: '#1890ff' }}>
                墨客运维助手
              </div>
              <div style={{ fontSize: 18, color: '#aaa', fontWeight: 400 }}>
                MoKe
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#999' }}>
              <div style={{ marginBottom: 4 }}>
                智能内容创作与自动化运营平台
              </div>
              <div>
                Version 1.0.0 beta
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* 调度器控制 */}
      <div style={{ marginBottom: 24 }}>
        <DispatcherControl />
      </div>

      {/* 任务列表 */}
      <TaskList
        onEdit={handleEdit}
        onLogin={handleLogin}
        onViewLogs={handleViewLogs}
        onViewResources={handleViewResources}
      />

      {/* 创建任务对话框 */}
      <CreateTaskForm
        open={createTaskOpen}
        onCancel={() => setCreateTaskOpen(false)}
      />

      {/* 编辑任务对话框 */}
      <EditTaskForm
        open={editTaskOpen}
        task={currentTask}
        onCancel={() => {
          setEditTaskOpen(false);
          setCurrentTask(null);
        }}
      />

      {/* 登录对话框 */}
      <LoginDialog
        open={loginDialogOpen}
        task={currentTask}
        onCancel={() => {
          setLoginDialogOpen(false);
          setCurrentTask(null);
        }}
        onSuccess={handleLoginSuccess}
      />

      {/* 日志查看器 */}
      <LogViewer
        open={logViewerOpen}
        task={currentTask}
        onCancel={() => {
          setLogViewerOpen(false);
          setCurrentTask(null);
        }}
      />

      {/* 资源管理器 */}
      <ResourceManager
        open={resourceManagerOpen}
        task={currentTask}
        onCancel={() => {
          setResourceManagerOpen(false);
          setCurrentTask(null);
        }}
      />
    </div>
  );
};
