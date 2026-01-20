import React, { useEffect, useState } from 'react';
import { Modal, Typography, Spin } from 'antd';
import { ReadOutlined } from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

interface HelpDialogProps {
  open: boolean;
  onCancel: () => void;
}

export const HelpDialog: React.FC<HelpDialogProps> = ({ open, onCancel }) => {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      loadHelpContent();
    }
  }, [open]);

  const loadHelpContent = async () => {
    setLoading(true);
    try {
      // 直接使用 axios 获取文本响应，绕过 API 拦截器
      const axios = (await import('axios')).default;
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
      const response = await axios.get<string>(`${API_BASE_URL}/help/guide`, {
        responseType: 'text',
      });
      setContent(response.data);
    } catch (error: any) {
      console.error('加载帮助文档失败:', error);
      setContent('# AIMediaOps 使用指南\n\n加载帮助文档失败，请稍后重试。\n\n错误信息：' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  // 简单的 Markdown 转 HTML（仅处理标题、段落、列表、代码块等基本格式）
  const renderMarkdown = (text: string) => {
    if (!text) return null;

    // 分割成段落
    const sections = text.split(/\n\n+/);
    
    return (
      <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
        {sections.map((section, index) => {
          const trimmed = section.trim();
          if (!trimmed) return null;

          // 处理标题
          if (trimmed.match(/^### /)) {
            return (
              <Title key={index} level={4} style={{ marginTop: index > 0 ? 24 : 0 }}>
                {trimmed.replace(/^### /, '')}
              </Title>
            );
          }
          if (trimmed.match(/^## /)) {
            return (
              <Title key={index} level={3} style={{ marginTop: index > 0 ? 24 : 0 }}>
                {trimmed.replace(/^## /, '')}
              </Title>
            );
          }
          if (trimmed.match(/^# /)) {
            return (
              <Title key={index} level={2} style={{ marginTop: index > 0 ? 24 : 0 }}>
                {trimmed.replace(/^# /, '')}
              </Title>
            );
          }

          // 处理列表
          if (trimmed.includes('\n- ') || trimmed.includes('\n1. ')) {
            const lines = trimmed.split('\n');
            const listItems = lines.filter(line => line.trim().match(/^[-*] |^\d+\. /));
            if (listItems.length > 0) {
              return (
                <ul key={index} style={{ marginTop: index > 0 ? 16 : 0, paddingLeft: 24 }}>
                  {listItems.map((item, itemIndex) => (
                    <li key={itemIndex} style={{ marginBottom: 8 }}>
                      {item.replace(/^[-*] |^\d+\. /, '')}
                    </li>
                  ))}
                </ul>
              );
            }
          }

          // 处理代码块
          if (trimmed.startsWith('```')) {
            const lines = trimmed.split('\n');
            const code = lines.slice(1, -1).join('\n');
            return (
              <pre key={index} style={{ 
                background: '#f5f5f5', 
                padding: 12, 
                borderRadius: 4,
                overflow: 'auto',
                marginTop: index > 0 ? 16 : 0
              }}>
                <code>{code}</code>
              </pre>
            );
          }

          // 处理普通段落
          const lines = trimmed.split('\n');
          return (
            <div key={index} style={{ marginTop: index > 0 ? 16 : 0 }}>
              {lines.map((line, lineIndex) => {
                // 处理加粗文本
                const parts = line.split(/(\*\*.*?\*\*)/);
                return (
                  <Paragraph key={lineIndex} style={{ marginBottom: 8 }}>
                    {parts.map((part, partIndex) => {
                      if (part.match(/\*\*.*?\*\*/)) {
                        return <Text strong key={partIndex}>{part.replace(/\*\*/g, '')}</Text>;
                      }
                      return <span key={partIndex}>{part}</span>;
                    })}
                  </Paragraph>
                );
              })}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Modal
      title={
        <span>
          <ReadOutlined style={{ marginRight: 8 }} />
          帮助文档
        </span>
      }
      open={open}
      onCancel={onCancel}
      footer={null}
      width={800}
      style={{ top: 20 }}
      styles={{
        body: {
          maxHeight: 'calc(100vh - 200px)',
          overflow: 'auto'
        }
      }}
    >
      <Spin spinning={loading}>
        <Typography>
          {content ? renderMarkdown(content) : null}
        </Typography>
      </Spin>
    </Modal>
  );
};
