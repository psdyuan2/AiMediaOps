import React, { useEffect, useState } from 'react';
import { Modal, Spin } from 'antd';
import { ReadOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';

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
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8765/api/v1';
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

  // 处理图片路径，将相对路径转换为后端 API 路径
  const processImageUrl = (src: string) => {
    // 如果已经是完整 URL，直接返回
    if (src.startsWith('http://') || src.startsWith('https://') || src.startsWith('data:')) {
      return src;
    }
    
    // 提取文件名（去掉路径前缀）
    const filename = src.split('/').pop() || src;
    
    // 转换为后端 API 路径
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8765/api/v1';
    return `${API_BASE_URL}/help/images/${filename}`;
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
      width={900}
      style={{ top: 20 }}
      styles={{
        body: {
          maxHeight: 'calc(100vh - 200px)',
          overflow: 'auto',
          padding: '24px',
        }
      }}
    >
      <Spin spinning={loading}>
        <div style={{ 
          maxHeight: 'calc(100vh - 250px)', 
          overflow: 'auto',
          lineHeight: '1.8',
        }}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw, rehypeSanitize]}
            components={{
              img: ({ src, alt }) => {
                const imageUrl = src ? processImageUrl(src) : '';
                return (
                  <img
                    src={imageUrl}
                    alt={alt || ''}
                    style={{
                      maxWidth: '100%',
                      height: 'auto',
                      margin: '16px 0',
                      borderRadius: '4px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                    }}
                    onError={(e) => {
                      console.error('图片加载失败:', imageUrl);
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                );
              },
              h1: ({ children }) => (
                <h1 style={{ fontSize: '28px', fontWeight: 'bold', marginTop: '24px', marginBottom: '16px' }}>
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginTop: '24px', marginBottom: '12px' }}>
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 style={{ fontSize: '20px', fontWeight: 'bold', marginTop: '20px', marginBottom: '10px' }}>
                  {children}
                </h3>
              ),
              h4: ({ children }) => (
                <h4 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '16px', marginBottom: '8px' }}>
                  {children}
                </h4>
              ),
              p: ({ children }) => (
                <p style={{ marginBottom: '12px', lineHeight: '1.8' }}>
                  {children}
                </p>
              ),
              ul: ({ children }) => (
                <ul style={{ marginBottom: '12px', paddingLeft: '24px', lineHeight: '1.8' }}>
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol style={{ marginBottom: '12px', paddingLeft: '24px', lineHeight: '1.8' }}>
                  {children}
                </ol>
              ),
              li: ({ children }) => (
                <li style={{ marginBottom: '6px' }}>
                  {children}
                </li>
              ),
              code: ({ children, ...props }: any) => {
                const isInline = !props.className?.includes('language-');
                if (isInline) {
                  return (
                    <code style={{
                      background: '#f5f5f5',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      fontFamily: 'monospace',
                      fontSize: '0.9em',
                    }}>
                      {children}
                    </code>
                  );
                }
                return (
                  <code style={{
                    display: 'block',
                    background: '#f5f5f5',
                    padding: '12px',
                    borderRadius: '4px',
                    overflow: 'auto',
                    marginBottom: '12px',
                    fontFamily: 'monospace',
                  }}>
                    {children}
                  </code>
                );
              },
              blockquote: ({ children }) => (
                <blockquote style={{
                  borderLeft: '4px solid #1890ff',
                  paddingLeft: '16px',
                  margin: '16px 0',
                  color: '#666',
                  fontStyle: 'italic',
                }}>
                  {children}
                </blockquote>
              ),
              strong: ({ children }) => (
                <strong style={{ fontWeight: 'bold' }}>
                  {children}
                </strong>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </Spin>
    </Modal>
  );
};
