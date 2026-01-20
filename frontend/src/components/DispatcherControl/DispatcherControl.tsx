import React, { useEffect } from 'react';
import { Card, Button, Statistic, Row, Col, Space } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { useDispatcherStore } from '@/store/dispatcherStore';

export const DispatcherControl: React.FC = () => {
  const { status, loading, fetchStatus, startDispatcher, stopDispatcher } = useDispatcherStore();

  useEffect(() => {
    fetchStatus();
    // 每5秒刷新一次状态
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  if (!status) {
    return <Card loading={loading}>加载中...</Card>;
  }

  return (
    <Card>
      <Row gutter={16} align="middle">
        <Col>
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={startDispatcher}
              disabled={status.is_running || loading}
              loading={loading}
            >
              启动调度器
            </Button>
            <Button
              danger
              icon={<PauseCircleOutlined />}
              onClick={stopDispatcher}
              disabled={!status.is_running || loading}
              loading={loading}
            >
              停止调度器
            </Button>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={fetchStatus}
              loading={loading}
            >
              刷新状态
            </Button>
          </Space>
        </Col>
        <Col flex="auto" />
        <Col>
          <Space size="large">
            <Statistic title="总任务" value={status.total_tasks} />
            <Statistic title="运行中" value={status.running_tasks} />
            <Statistic
              title="状态"
              value={status.is_running ? '运行中' : '已停止'}
              valueStyle={{ color: status.is_running ? '#3f8600' : '#cf1322' }}
            />
          </Space>
        </Col>
      </Row>
    </Card>
  );
};
