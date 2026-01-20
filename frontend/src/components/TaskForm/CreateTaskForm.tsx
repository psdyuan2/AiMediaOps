import React, { useEffect } from 'react';
import { Modal, Form, Input, InputNumber, DatePicker, Space, Button, Switch, Radio } from 'antd';
import { useTaskStore } from '@/store/taskStore';
import type { TaskCreateRequest, TaskMode } from '@/types/task';
import dayjs from 'dayjs';
import { useLicenseStore } from '@/store/licenseStore';

interface CreateTaskFormProps {
  open: boolean;
  onCancel: () => void;
  defaultInterval?: number;
  defaultEndTime?: string;
}

export const CreateTaskForm: React.FC<CreateTaskFormProps> = ({
  open,
  onCancel,
  defaultInterval = 3600,
  defaultEndTime,
}) => {
  const [form] = Form.useForm();
  const { createTask } = useTaskStore();
  const [loading, setLoading] = React.useState(false);
  const [timeRangeUnlimited, setTimeRangeUnlimited] = React.useState(false);
  const [mode, setMode] = React.useState<TaskMode>('standard');
  const { licenseStatus } = useLicenseStore();
  const isActivated = licenseStatus?.activated ?? false;

  const effectiveInterval = isActivated ? defaultInterval : 7200;

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        interval: effectiveInterval,
        task_end_time: defaultEndTime ? dayjs(defaultEndTime) : dayjs().add(30, 'day'),
        valid_time_range: [8, 22],
        mode: 'standard',
        interaction_note_count: 3,
      });
      setTimeRangeUnlimited(false);
      setMode('standard');
    }
  }, [open, effectiveInterval, defaultEndTime, form]);

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      const data: TaskCreateRequest = {
        sys_type: 'mac_intel', // 默认值，可以从系统检测
        task_type: 'xhs_type',
        xhs_account_id: values.xhs_account_id,
        xhs_account_name: values.xhs_account_name,
        user_query: values.user_query,
        user_topic: values.user_topic,
        user_style: values.user_style,
        user_target_audience: values.user_target_audience,
        task_end_time: values.task_end_time ? values.task_end_time.format('YYYY-MM-DD') : undefined,
        interval: values.interval,
        valid_time_range: timeRangeUnlimited ? null : values.valid_time_range,
        mode: values.mode || 'standard',
        interaction_note_count: values.interaction_note_count || 3,
      };
      await createTask(data);
      form.resetFields();
      onCancel();
    } catch (error) {
      // 错误已在 store 中处理
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="新建任务"
      open={open}
      onCancel={onCancel}
      footer={null}
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          interval: defaultInterval,
          task_end_time: defaultEndTime ? dayjs(defaultEndTime) : dayjs().add(30, 'day'),
          valid_time_range: [8, 22],
        }}
      >
        <Form.Item
          name="xhs_account_id"
          label="账户ID"
          rules={[{ required: true, message: '请输入账户ID' }]}
        >
          <Input placeholder="account_1" />
        </Form.Item>

        <Form.Item
          name="xhs_account_name"
          label="账户名称"
          rules={[{ required: true, message: '请输入账户名称' }]}
        >
          <Input placeholder="账号1" />
        </Form.Item>

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
          rules={[
            { required: true, message: '请输入执行间隔' }, 
            { type: 'number', min: 900, message: '最小间隔为15分钟（900秒）' },
            { type: 'number', max: 10800, message: '最大间隔为3小时（10800秒）' }
          ]}
        >
          <InputNumber
            min={900}
            max={10800}
            step={900}
            style={{ width: '100%' }}
            disabled={!isActivated}
          />
        </Form.Item>
        {!isActivated && (
          <div style={{ color: '#ff9800', fontSize: 12, marginTop: -16, marginBottom: 16 }}>
            免费试用版执行间隔固定为2小时（7200秒），激活后可自定义
          </div>
        )}

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
          initialValue="standard"
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
            initialValue={3}
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
              创建
            </Button>
            <Button onClick={onCancel}>取消</Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};
