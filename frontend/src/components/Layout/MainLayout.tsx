import React, { useState, useEffect } from 'react';
import { Layout } from 'antd';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { HelpDialog } from '@/components/HelpDialog';
import { LicenseActivateDialog } from '@/components/LicenseActivateDialog';
import { StartupCard } from '@/components/StartupCard';
import { Outlet } from 'react-router-dom';
import { registerActivateDialog } from '@/services/api';
import { useLicenseStore } from '@/store/licenseStore';

const { Content } = Layout;

export const MainLayout: React.FC = () => {
  const [helpDialogOpen, setHelpDialogOpen] = useState(false);
  // const [licensePurchaseOpen, setLicensePurchaseOpen] = useState(false);
  const [activateDialogOpen, setActivateDialogOpen] = useState(false);
  const [startupComplete, setStartupComplete] = useState(false);
  const { fetchLicenseStatus } = useLicenseStore();

  useEffect(() => {
    const handleShowHelp = () => {
      setHelpDialogOpen(true);
    };

    window.addEventListener('showHelpDialog' as any, handleShowHelp as EventListener);
    return () => {
      window.removeEventListener('showHelpDialog' as any, handleShowHelp as EventListener);
    };
  }, []);

  // 注册激活对话框打开函数 & 监听相关自定义事件
  useEffect(() => {
    registerActivateDialog(() => {
      setActivateDialogOpen(true);
      // 每次打开激活对话框时，刷新一次 license 状态
      fetchLicenseStatus();
    });

    // const handleShowLicensePurchase = () => {
    //   setLicensePurchaseOpen(true);
    // };

    const handleOpenActivateDialog = () => {
      setActivateDialogOpen(true);
      fetchLicenseStatus();
    };

    // window.addEventListener('showLicensePurchase' as any, handleShowLicensePurchase as EventListener);
    window.addEventListener('openActivateDialog' as any, handleOpenActivateDialog as EventListener);
    return () => {
      // window.removeEventListener('showLicensePurchase' as any, handleShowLicensePurchase as EventListener);
      window.removeEventListener('openActivateDialog' as any, handleOpenActivateDialog as EventListener);
    };
  }, [fetchLicenseStatus]);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 启动卡片 - 只在 Electron 环境中且未完成启动时显示 */}
      {!startupComplete && <StartupCard onReady={() => setStartupComplete(true)} />}
      
      <Header onShowHelp={() => setHelpDialogOpen(true)} />
      <Layout>
        <Sidebar />
        <Content style={{ 
          padding: '24px', 
          background: '#f0f2f5',
          overflow: 'auto'
        }}>
          <Outlet />
        </Content>
      </Layout>
      
      {/* 帮助文档对话框 */}
      <HelpDialog
        open={helpDialogOpen}
        onCancel={() => setHelpDialogOpen(false)}
      />

      {/* 激活码激活对话框 */}
      <LicenseActivateDialog
        open={activateDialogOpen}
        onClose={() => setActivateDialogOpen(false)}
      />
    </Layout>
  );
};
