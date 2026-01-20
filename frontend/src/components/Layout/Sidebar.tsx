import React, { useEffect } from 'react';
import { Layout, Slider, DatePicker, Button, Space, InputNumber, Switch, Radio } from 'antd';
import { PlusOutlined, ShoppingOutlined } from '@ant-design/icons';
import { useTaskStore } from '@/store/taskStore';
import type { TaskMode } from '@/types/task';
import dayjs from 'dayjs';
import { useLicenseStore } from '@/store/licenseStore';
import { LicenseCard } from '@/components/LicenseCard';

const { Sider } = Layout;

export const Sidebar: React.FC = () => {
  const { selectedTask } = useTaskStore();
  const { licenseStatus, fetchLicenseStatus } = useLicenseStore();
  const isActivated = licenseStatus?.activated ?? false;
  const [interval, setInterval] = React.useState(3600);
  const [endTime, setEndTime] = React.useState<dayjs.Dayjs | null>(null);
  const [timeRangeUnlimited, setTimeRangeUnlimited] = React.useState(false);
  const [timeRangeStart, setTimeRangeStart] = React.useState(8);
  const [timeRangeEnd, setTimeRangeEnd] = React.useState(22);
  const [mode, setMode] = React.useState<TaskMode>('standard');
  const [interactionNoteCount, setInteractionNoteCount] = React.useState(3);

  const [licenseCardVisible, setLicenseCardVisible] = React.useState(false);

  // 当选中任务变化时，更新表单值
  useEffect(() => {
    if (selectedTask) {
      // 确保interval在新范围内（15分钟到3小时）
      const taskInterval = selectedTask.interval;
      const clampedInterval = Math.max(900, Math.min(10800, taskInterval));
      setInterval(clampedInterval);
      setEndTime(selectedTask.task_end_time ? dayjs(selectedTask.task_end_time) : null);
      
      // 更新时间范围设置
      if (selectedTask.valid_time_range === null || selectedTask.valid_time_range === undefined) {
        setTimeRangeUnlimited(true);
        setTimeRangeStart(8);
        setTimeRangeEnd(22);
      } else {
        setTimeRangeUnlimited(false);
        setTimeRangeStart(selectedTask.valid_time_range[0]);
        setTimeRangeEnd(selectedTask.valid_time_range[1]);
      }
      
      // 更新模式和互动数量
      setMode(selectedTask.mode || 'standard');
      setInteractionNoteCount(selectedTask.interaction_note_count || 3);
    } else {
      // 未选中任务时，使用默认值（1小时）
      setInterval(3600);
      setEndTime(null);
      setTimeRangeUnlimited(false);
      setTimeRangeStart(8);
      setTimeRangeEnd(22);
      setMode('standard');
      setInteractionNoteCount(3);
    }
  }, [selectedTask]);

  // 打开侧边栏时预取 license 状态（只拉一次）
  useEffect(() => {
    if (!licenseStatus) {
      fetchLicenseStatus();
    }
  }, [licenseStatus, fetchLicenseStatus]);

  const handleIntervalChange = (value: number) => {
    // 确保值在新范围内（15分钟到3小时）
    const clampedValue = Math.max(900, Math.min(10800, value));
    setInterval(clampedValue);
    if (selectedTask) {
      // 实时保存
      useTaskStore.getState().updateTask(selectedTask.task_id, { interval: clampedValue });
    }
  };

  const handleEndTimeChange = (date: dayjs.Dayjs | null) => {
    setEndTime(date);
    if (selectedTask && date) {
      // 实时保存
      useTaskStore.getState().updateTask(selectedTask.task_id, { 
        task_end_time: date.format('YYYY-MM-DD') 
      });
    }
  };

  const handleTimeRangeUnlimitedChange = (checked: boolean) => {
    setTimeRangeUnlimited(checked);
    if (selectedTask) {
      // 实时保存
      useTaskStore.getState().updateTask(selectedTask.task_id, { 
        valid_time_range: checked ? null : [timeRangeStart, timeRangeEnd]
      });
    }
  };

  const handleTimeRangeChange = (start: number | null, end: number | null) => {
    const newStart = start !== null ? start : timeRangeStart;
    const newEnd = end !== null ? end : timeRangeEnd;
    
    if (start !== null) setTimeRangeStart(start);
    if (end !== null) setTimeRangeEnd(end);
    
    if (selectedTask && !timeRangeUnlimited) {
      // 实时保存
      useTaskStore.getState().updateTask(selectedTask.task_id, { 
        valid_time_range: [newStart, newEnd]
      });
    }
  };

  const handleModeChange = (newMode: TaskMode) => {
    setMode(newMode);
    if (selectedTask) {
      // 实时保存
      useTaskStore.getState().updateTask(selectedTask.task_id, { mode: newMode });
    }
  };

  const handleInteractionNoteCountChange = (value: number | null) => {
    const clampedValue = value !== null ? Math.max(1, Math.min(5, value)) : 3;
    setInteractionNoteCount(clampedValue);
    if (selectedTask) {
      // 实时保存
      useTaskStore.getState().updateTask(selectedTask.task_id, { 
        interaction_note_count: clampedValue 
      });
    }
  };

  const handleCreateTask = () => {
    // 打开创建任务对话框（由父组件处理）
    const event = new CustomEvent('openCreateTaskDialog', { 
      detail: { interval, endTime: endTime?.format('YYYY-MM-DD') } 
    });
    window.dispatchEvent(event);
  };

  return (
    <Sider 
      width={256} 
      style={{ 
        background: '#fafafa',
        borderRight: '1px solid #f0f0f0',
        padding: '24px',
        overflow: 'auto'
      }}
    >
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 24 }}>设置</h2>
      
      {/* Interval 滑块 */}
      <div style={{ marginBottom: 24 }}>
        <label
          style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 14, 
          fontWeight: 500, 
          marginBottom: 8,
            color: '#333',
          }}
        >
          <span>执行间隔</span>
          <span style={{ fontSize: 12, color: '#999', fontWeight: 400 }}>单位(秒)</span>
          {!isActivated && (
            <span style={{ fontSize: 12, color: '#ff9800', marginLeft: 8 }}>
              免费试用：固定2小时
            </span>
          )}
        </label>
        <div style={{ position: 'relative', padding: '0 4px' }}>
          <Slider
            min={900}
            max={10800}
            step={900}
            value={interval}
            onChange={handleIntervalChange}
            disabled={!selectedTask || !isActivated}
            marks={(() => {
              // 每15分钟（900秒）添加一个白色小点作为刻度
              const marks: Record<number, any> = {};
              for (let i = 900; i <= 10800; i += 900) {
                marks[i] = {
                  style: {
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: '#fff',
                    border: '1px solid #d9d9d9',
                    marginTop: '-3px',
                    marginLeft: '-3px',
                  },
                };
              }
              return marks;
            })()}
          />
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            fontSize: 12, 
            color: '#999',
            marginTop: 8
          }}>
            <span>15分钟</span>
            <span>3小时</span>
          </div>
        </div>
      </div>
      
      {/* 有效时间范围选择器 */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ 
          display: 'block', 
          fontSize: 14, 
          fontWeight: 500, 
          marginBottom: 8,
          color: '#333'
        }}>
          有效时间范围
        </label>
        <div style={{ marginBottom: 8 }}>
          <Space>
            <span style={{ fontSize: 12, color: '#666' }}>无限制</span>
            <Switch
              checked={timeRangeUnlimited}
              onChange={handleTimeRangeUnlimitedChange}
              disabled={!selectedTask}
              size="small"
            />
          </Space>
        </div>
        {!timeRangeUnlimited && (
          <Space.Compact style={{ display: 'flex', width: '100%' }}>
            <InputNumber
              min={0}
              max={23}
              value={timeRangeStart}
              onChange={(value) => handleTimeRangeChange(value, null)}
              disabled={!selectedTask}
              placeholder="开始小时"
              style={{ flex: 1 }}
            />
            <span style={{ lineHeight: '32px', color: '#999', padding: '0 8px' }}>~</span>
            <InputNumber
              min={0}
              max={23}
              value={timeRangeEnd}
              onChange={(value) => handleTimeRangeChange(null, value)}
              disabled={!selectedTask}
              placeholder="结束小时"
              style={{ flex: 1 }}
            />
          </Space.Compact>
        )}
      </div>
      
      {/* 执行模式选择器 */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ 
          display: 'block', 
          fontSize: 14, 
          fontWeight: 500, 
          marginBottom: 8,
          color: '#333'
        }}>
          执行模式
        </label>
        <Radio.Group
          value={mode}
          onChange={(e) => handleModeChange(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          disabled={!selectedTask}
          style={{ width: '100%' }}
        >
          <Radio.Button value="standard" style={{ flex: 1 }}>标准</Radio.Button>
          <Radio.Button value="interaction" style={{ flex: 1 }}>互动</Radio.Button>
          <Radio.Button value="publish" style={{ flex: 1 }}>发布</Radio.Button>
        </Radio.Group>
        <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
          {mode === 'standard' && '互动 + 发布笔记'}
          {mode === 'interaction' && '仅执行互动操作'}
          {mode === 'publish' && '仅发布笔记'}
        </div>
      </div>
      
      {/* 互动笔记数量配置（仅在标准模式和互动模式下显示） */}
      {(mode === 'standard' || mode === 'interaction') && (
        <div style={{ marginBottom: 24 }}>
          <label style={{ 
            display: 'block', 
            fontSize: 14, 
            fontWeight: 500, 
            marginBottom: 8,
            color: '#333'
          }}>
            互动笔记数量
          </label>
          <InputNumber
            min={1}
            max={5}
            value={interactionNoteCount}
            onChange={handleInteractionNoteCountChange}
            disabled={!selectedTask}
            style={{ width: '100%' }}
          />
          <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
            范围：1-5，默认3
          </div>
        </div>
      )}
      
      {/* End Time 选择器 */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ 
          display: 'block', 
          fontSize: 14, 
          fontWeight: 500, 
          marginBottom: 8,
          color: '#333'
        }}>
          结束时间
        </label>
        <DatePicker
          style={{ width: '100%' }}
          value={endTime}
          onChange={handleEndTimeChange}
          disabled={!selectedTask}
          format="YYYY-MM-DD"
        />
      </div>
      
      {/* 操作按钮 + 套餐卡片（相对于按钮定位） */}
      <div style={{ position: 'relative' }}>
        <Space orientation="vertical" style={{ width: '100%' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          block
          onClick={handleCreateTask}
          style={{ marginBottom: 8 }}
        >
          新建任务
        </Button>
        <Button
          icon={<ShoppingOutlined />}
          block
            onClick={() => setLicenseCardVisible(true)}
        >
          查看当前套餐
        </Button>
      </Space>

        {/* 套餐信息卡片：点击“激活码激活”时，关闭卡片并弹出激活对话框 */}
        <LicenseCard
          open={licenseCardVisible}
          onClose={() => setLicenseCardVisible(false)}
          onActivate={() => {
            setLicenseCardVisible(false);
            // 通知主布局打开激活对话框
            const event = new CustomEvent('openActivateDialog' as any);
            window.dispatchEvent(event);
          }}
          onPurchase={() => {
            const event = new CustomEvent('showLicensePurchase' as any);
            window.dispatchEvent(event);
          }}
        />
      </div>
    </Sider>
  );
};
