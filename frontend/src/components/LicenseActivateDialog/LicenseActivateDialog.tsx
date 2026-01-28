import React, { useState } from 'react';
import { Modal, Form, Input } from 'antd';
import { useLicenseStore } from '@/store/licenseStore';

interface LicenseActivateDialogProps {
  open: boolean;
  onClose: () => void;
}

export const LicenseActivateDialog: React.FC<LicenseActivateDialogProps> = ({
  open,
  onClose,
}) => {
  const [form] = Form.useForm();
  const { activate, loading } = useLicenseStore();
  const [submitting, setSubmitting] = useState(false);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const success = await activate(values.license_code);
      if (success) {
        form.resetFields();
        onClose();
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title="激活码激活"
      open={open}
      onCancel={onClose}
      onOk={handleOk}
      confirmLoading={submitting || loading}
      okText="立即激活"
      cancelText="取消"
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="license_code"
          label="激活码"
          rules={[
            { required: true, message: '请输入激活码' },
            { min: 8, message: '激活码格式不正确' },
          ]}
        >
          <Input placeholder="请输入激活码" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

