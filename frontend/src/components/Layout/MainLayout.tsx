import React, { useState, useEffect } from 'react';
import { Layout } from 'antd';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { HelpDialog } from '@/components/HelpDialog';
import { Outlet } from 'react-router-dom';

const { Content } = Layout;

export const MainLayout: React.FC = () => {
  const [helpDialogOpen, setHelpDialogOpen] = useState(false);

  useEffect(() => {
    const handleShowHelp = () => {
      setHelpDialogOpen(true);
    };

    window.addEventListener('showHelpDialog' as any, handleShowHelp as EventListener);
    return () => {
      window.removeEventListener('showHelpDialog' as any, handleShowHelp as EventListener);
    };
  }, []);

  return (
    <Layout style={{ minHeight: '100vh' }}>
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
    </Layout>
  );
};
