import React, { useEffect } from 'react';
import { Modal, Form, Input, InputNumber, DatePicker, Space, Button, Switch, Radio } from 'antd';
import { useTaskStore } from '@/store/taskStore';
import type { Task, TaskUpdateRequest, TaskMode } from '@/types/task';
import dayjs from 'dayjs';

interface EditTaskFormProps {
  open: boolean;
  task: Task | null;
  onCancel: () => void;
}

export const EditTaskForm: React.FC<EditTaskFormProps> = ({
  open,
  task,
  onCancel,
}) => {
  const [form] = Form.useForm();
  const { updateTask } = useTaskStore();
  const [loading, setLoading] = React.useState(false);
  const [timeRangeUnlimited, setTimeRangeUnlimited] = React.useState(false);
  const [mode, setMode] = React.useState<TaskMode>('standard');

  useEffect(() => {
    if (open && task) {
      const isUnlimited = task.valid_time_range === null || task.valid_time_range === undefined;
      setTimeRangeUnlimited(isUnlimited);
      form.setFieldsValue({
        user_query: task.kwargs?.user_query || '',
        user_topic: task.kwargs?.user_topic || '',
        user_style: task.kwargs?.user_style || '',
        user_target_audience: task.kwargs?.user_target_audience || '',
        task_end_time: task.task_end_time ? dayjs(task.task_end_time) : null,
        interval: task.interval,
        valid_time_range: isUnlimited ? [8, 22] : task.valid_time_range,
        mode: task.mode || 'standard',
        interaction_note_count: task.interaction_note_count || 3,
      });
      setMode(task.mode || 'standard');
    }
  }, [open, task, form]);

  const handleSubmit = async (values: any) => {
    if (!task) return;
    
    setLoading(true);
    try {
      const data: TaskUpdateRequest = {
        user_query: values.user_query,
        user_topic: values.user_topic,
        user_style: values.user_style,
        user_target_audience: values.user_target_audience,
        task_end_time: values.task_end_time ? values.task_end_time.format('YYYY-MM-DD') : undefined,
        interval: values.interval,
        valid_time_range: timeRangeUnlimited ? null : values.valid_time_range,
        mode: values.mode,
        interaction_note_count: values.interaction_note_count,
      };
      await updateTask(task.task_id, data);
      onCancel();
    } catch (error) {
      // 错误已在 store 中处理
    } finally {
      setLoading(false);
    }
  };

  if (!task) return null;

  return (
    <Modal
      title={`编辑任务 - ${task.account_name || task.account_id}`}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <Form.Item name="user_query" label="账号运营要求">
          <Input placeholder="开始运营" />
        </Form.Item>

        <Form.Item 
          name="user_topic" 
          label="账号内容主题"
          rules={[{ required: true, message: '请输入账号内容主题（必填）' }]}
        >
          <Input placeholder="科技" />
        </Form.Item>

        <Form.Item name="user_style" label="内容风格">
          <Input placeholder="专业" />
        </Form.Item>

        <Form.Item name="user_target_audience" label="目标受众">
          <Input placeholder="技术爱好者" />
        </Form.Item>

        <Form.Item
          name="interval"
          label="执行间隔（秒）"
          rules={[{ required: true, message: '请输入执行间隔' }, { type: 'number', min: 60, message: '最小间隔为60秒' }]}
        >
          <InputNumber min={60} max={86400} step={60} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          name="valid_time_range"
          label="有效时间范围"
          rules={[
            ({ getFieldValue }) => ({
              validator: () => {
                if (timeRangeUnlimited) {
                  return Promise.resolve();
                }
                const range = getFieldValue('valid_time_range');
                if (!range || !Array.isArray(range) || range.length !== 2) {
                  return Promise.reject(new Error('请选择有效时间范围'));
                }
                return Promise.resolve();
              },
            }),
          ]}
        >
          <div>
            <div style={{ marginBottom: 8 }}>
              <Space>
                <span style={{ fontSize: 12, color: '#666' }}>无限制</span>
                <Switch
                  checked={timeRangeUnlimited}
                  onChange={setTimeRangeUnlimited}
                  size="small"
                />
              </Space>
            </div>
            {!timeRangeUnlimited && (
              <Space.Compact style={{ width: '100%' }}>
                <Form.Item name={[0]} noStyle>
                  <InputNumber min={0} max={23} placeholder="开始小时" style={{ width: '50%' }} />
                </Form.Item>
                <span style={{ lineHeight: '32px', color: '#999', padding: '0 8px' }}>~</span>
                <Form.Item name={[1]} noStyle>
                  <InputNumber min={0} max={23} placeholder="结束小时" style={{ width: '50%' }} />
                </Form.Item>
              </Space.Compact>
            )}
          </div>
        </Form.Item>

        <Form.Item name="task_end_time" label="任务结束时间">
          <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
        </Form.Item>

        <Form.Item
          name="mode"
          label="执行模式"
        >
          <Radio.Group 
            optionType="button" 
            buttonStyle="solid"
            onChange={(e) => setMode(e.target.value)}
          >
            <Radio.Button value="standard">标准模式</Radio.Button>
            <Radio.Button value="interaction">互动模式</Radio.Button>
            <Radio.Button value="publish">发布模式</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {(mode === 'standard' || mode === 'interaction') && (
          <Form.Item
            name="interaction_note_count"
            label="互动笔记数量"
            rules={[
              { required: true, message: '请输入互动笔记数量' },
              { type: 'number', min: 1, message: '最小值为1' },
              { type: 'number', max: 5, message: '最大值为5' }
            ]}
          >
            <InputNumber min={1} max={5} style={{ width: '100%' }} />
          </Form.Item>
        )}

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              保存
            </Button>
            <Button onClick={onCancel}>取消</Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};
