import React, { useEffect, useState } from 'react';
import { Modal, Tabs, Button, Space, Image, Input, Upload, message, Spin } from 'antd';
import { ReloadOutlined, DownloadOutlined, SaveOutlined, UploadOutlined } from '@ant-design/icons';
import { taskService } from '@/services/taskService';
import type { Task, ImageInfo } from '@/types/task';
import { formatFileSize } from '@/utils/format';

const { TextArea } = Input;

interface ResourceManagerProps {
  open: boolean;
  task: Task | null;
  onCancel: () => void;
}

export const ResourceManager: React.FC<ResourceManagerProps> = ({
  open,
  task,
  onCancel,
}) => {
  const [activeTab, setActiveTab] = useState('images');
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [sourceContent, setSourceContent] = useState('');
  const [sourceFileInfo, setSourceFileInfo] = useState<{ size?: number; modified_time?: string }>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && task) {
      if (activeTab === 'images') {
        loadImages();
      } else {
        loadSourceFile();
      }
    }
  }, [open, task, activeTab]);

  const loadImages = async () => {
    if (!task) return;
    
    setLoading(true);
    try {
      const response = await taskService.getTaskImages(task.task_id);
      setImages(response.images || []);
    } catch (error: any) {
      message.error('加载图片失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const loadSourceFile = async () => {
    if (!task) return;
    
    setLoading(true);
    try {
      const response = await taskService.getSourceFile(task.task_id);
      setSourceContent(response.content || '');
      setSourceFileInfo({
        size: response.size,
        modified_time: response.modified_time,
      });
    } catch (error: any) {
      message.error('加载知识库文件失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSource = async () => {
    if (!task) return;
    
    setSaving(true);
    try {
      await taskService.updateSourceFile(task.task_id, sourceContent);
      message.success('保存成功');
      loadSourceFile();
    } catch (error: any) {
      message.error('保存失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadSource = () => {
    if (!task) return;
    taskService.downloadSourceFile(task.task_id);
  };

  const handleUploadSource = async (file: File) => {
    if (!task) return false;
    
    try {
      await taskService.uploadSourceFile(task.task_id, file);
      message.success('上传成功');
      loadSourceFile();
      return false; // 阻止默认上传行为
    } catch (error: any) {
      message.error('上传失败: ' + (error.response?.data?.detail || error.message));
      return false;
    }
  };

  if (!task) return null;

  return (
    <Modal
      title={`资源管理 - ${task.account_name || task.account_id}`}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={900}
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'images',
            label: '图片',
            children: (
              <Spin spinning={loading}>
                <div style={{ marginBottom: 16 }}>
                  <Button icon={<ReloadOutlined />} onClick={loadImages}>
                    刷新
                  </Button>
                </div>
                {images.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                    暂无图片
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
                    {images.map((image) => (
                      <div key={image.filename} style={{ border: '1px solid #f0f0f0', borderRadius: 4, padding: 8 }}>
                        <Image
                          src={image.url}
                          alt={image.filename}
                          style={{ width: '100%', height: '150px', objectFit: 'cover', marginBottom: 8 }}
                          preview
                        />
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          <div>{image.filename}</div>
                          <div>{formatFileSize(image.size)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Spin>
            ),
          },
          {
            key: 'source',
            label: '知识库',
            children: (
              <Spin spinning={loading}>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space>
                    <Button icon={<ReloadOutlined />} onClick={loadSourceFile}>
                      刷新
                    </Button>
                    <Button icon={<DownloadOutlined />} onClick={handleDownloadSource}>
                      导出
                    </Button>
                    <Upload
                      beforeUpload={handleUploadSource}
                      showUploadList={false}
                    >
                      <Button icon={<UploadOutlined />}>
                        导入
                      </Button>
                    </Upload>
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      onClick={handleSaveSource}
                      loading={saving}
                    >
                      保存
                    </Button>
                  </Space>
                  {sourceFileInfo.size && (
                    <span style={{ fontSize: '12px', color: '#999' }}>
                      文件大小: {formatFileSize(sourceFileInfo.size)}
                    </span>
                  )}
                </div>
                <TextArea
                  value={sourceContent}
                  onChange={(e) => setSourceContent(e.target.value)}
                  rows={20}
                  style={{ fontFamily: 'monospace', fontSize: '12px' }}
                  placeholder="知识库内容..."
                />
              </Spin>
            ),
          },
        ]}
      />
    </Modal>
  );
};
