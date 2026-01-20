import React, { useEffect, useState } from 'react';
import { Modal, Button, Space, Image, message } from 'antd';
import { ReloadOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { taskService } from '@/services/taskService';
import type { Task } from '@/types/task';

interface LoginDialogProps {
  open: boolean;
  task: Task | null;
  onCancel: () => void;
  onSuccess?: () => void;
}

export const LoginDialog: React.FC<LoginDialogProps> = ({
  open,
  task,
  onCancel,
  onSuccess,
}) => {
  const [qrcodeUrl, setQrcodeUrl] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (open && task) {
      loadQrcode();
    } else {
      setQrcodeUrl('');
    }
  }, [open, task]);

  const loadQrcode = async () => {
    if (!task) return;
    
    setLoading(true);
    try {
      const response = await taskService.getLoginQrcode(task.task_id);
      setQrcodeUrl(response.qrcode_url);
    } catch (error: any) {
      message.error('加载二维码失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!task) return;
    
    setConfirming(true);
    try {
      const response = await taskService.confirmLogin(task.task_id);
      if (response.is_logged_in) {
        message.success('登录成功！');
        onSuccess?.();
        setTimeout(() => {
          onCancel();
        }, 2000);
      } else {
        message.error('登录失败，请重新扫码');
      }
    } catch (error: any) {
      message.error('检查登录状态失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setConfirming(false);
    }
  };

  if (!task) return null;

  return (
    <Modal
      title={`小红书登录 - ${task.account_name || task.account_id}`}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={400}
    >
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        {loading ? (
          <div>加载二维码中...</div>
        ) : qrcodeUrl ? (
          <>
            <Image src={qrcodeUrl} alt="登录二维码" style={{ maxWidth: '100%', marginBottom: 16 }} />
            <p style={{ color: '#666', marginBottom: 16 }}>
              请使用小红书App扫描上方二维码登录
            </p>
            <Space>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={handleConfirm}
                loading={confirming}
              >
                确认登录
              </Button>
              <Button icon={<ReloadOutlined />} onClick={loadQrcode}>
                刷新二维码
              </Button>
            </Space>
          </>
        ) : (
          <div>获取二维码失败</div>
        )}
      </div>
    </Modal>
  );
};
