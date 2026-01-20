import React, { useEffect } from 'react';
import { Card, Descriptions, Button, Tag, Space, Spin } from 'antd';
import dayjs from 'dayjs';
import { useLicenseStore } from '@/store/licenseStore';

interface LicenseCardProps {
  open: boolean;
  onClose: () => void;
  onActivate: () => void;
  onPurchase: () => void;
}

export const LicenseCard: React.FC<LicenseCardProps> = ({
  open,
  onClose,
  onActivate,
  onPurchase,
}) => {
  const { licenseStatus, loading, fetchLicenseStatus } = useLicenseStore();

  useEffect(() => {
    if (open && !licenseStatus && !loading) {
      fetchLicenseStatus();
    }
  }, [open, licenseStatus, loading, fetchLicenseStatus]);

  if (!open) return null;

  const activated = licenseStatus?.activated ?? false;
  const expired = licenseStatus?.expired ?? false;
  const isFreeTrial = licenseStatus?.is_free_trial ?? !activated;

  const endTime = licenseStatus?.config?.end_time
    ? dayjs(licenseStatus.config.end_time).format('YYYY-MM-DD HH:mm')
    : '-';

  const maxTasks = licenseStatus?.max_tasks ?? 1;
  const currentTasks = licenseStatus?.current_tasks ?? 0;
  const remaining = licenseStatus?.remaining_tasks ?? Math.max(0, maxTasks - currentTasks);

  const statusTag = (() => {
    if (expired) return <Tag color="red">已过期</Tag>;
    if (activated) return <Tag color="green">已激活</Tag>;
    return <Tag color="blue">未激活 · 免费试用</Tag>;
  })();

  const title = (
    <Space>
      <span>当前套餐</span>
      {statusTag}
    </Space>
  );

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0, 0, 0, 0.20)', // 半透明遮罩，弱化背景
      }}
      onClick={onClose}
    >
      <Card
        title={title}
        extra={
          <Button type="text" size="small" onClick={onClose}>
            关闭
          </Button>
        }
        style={{
          width: 420,
          maxWidth: '90vw',
          background: '#f7f7f7', // 比页面白色略深，方便区分
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.16)',
        }}
        styles={{
          body: {
            padding: 20,
          },
        }}
        onClick={(e) => e.stopPropagation()} // 阻止冒泡，避免点内容就关闭
      >
        <Spin spinning={loading}>
          <Descriptions column={1} size="small" colon={false}>
            {isFreeTrial ? (
              <>
                <Descriptions.Item label="套餐类型">免费试用</Descriptions.Item>
                <Descriptions.Item label="可创建任务数">1 个</Descriptions.Item>
                <Descriptions.Item label="执行间隔">
                  固定 2 小时（7200 秒）
                </Descriptions.Item>
                <Descriptions.Item label="立即执行">不支持</Descriptions.Item>
              </>
            ) : (
              <>
                <Descriptions.Item label="套餐类型">
                  {licenseStatus?.config?.is_free ? '免费套餐' : '付费套餐'}
                </Descriptions.Item>
                <Descriptions.Item label="到期时间">{endTime}</Descriptions.Item>
                <Descriptions.Item label="任务数量">
                  {currentTasks} / {maxTasks}（剩余 {remaining}）
                </Descriptions.Item>
                {typeof licenseStatus?.config?.price === 'number' && (
                  <Descriptions.Item label="订阅价格">
                    {licenseStatus.config.price} 元
                  </Descriptions.Item>
                )}
              </>
            )}
          </Descriptions>

          <div style={{ marginTop: 20, textAlign: 'right' }}>
            <Space>
              <Button onClick={onPurchase}>激活码购买</Button>
              <Button type="primary" onClick={onActivate}>
                激活码激活
              </Button>
            </Space>
          </div>
        </Spin>
      </Card>
    </div>
  );
};

