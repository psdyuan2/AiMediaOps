import React from 'react';
import { Layout, Button } from 'antd';
import { ReadOutlined } from '@ant-design/icons';
import logoImage from '@/assets/Group 1.png';

const { Header: AntHeader } = Layout;

interface HeaderProps {
  onShowHelp?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onShowHelp }) => {
  const handleShowHelp = () => {
    // 触发帮助文档显示事件
    const event = new CustomEvent('showHelpDialog');
    window.dispatchEvent(event);
    if (onShowHelp) {
      onShowHelp();
    }
  };

  return (
    <AntHeader style={{ 
      background: '#fff', 
      borderBottom: '1px solid #f0f0f0',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <img 
          src={logoImage} 
          alt="MoKe Logo" 
          style={{ 
            width: 32, 
            height: 32, 
            marginRight: 12,
            objectFit: 'contain'
          }} 
        />
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
          <span style={{ fontSize: 18, fontWeight: 600 }}>墨客运维助手</span>
          <span style={{ fontSize: 12, color: '#999', fontWeight: 400 }}>MoKe</span>
        </div>
      </div>
      <div>
        <Button 
          type="text" 
          icon={<ReadOutlined />}
          onClick={handleShowHelp}
          style={{ color: '#666' }}
        >
          帮助文档
        </Button>
      </div>
    </AntHeader>
  );
};
