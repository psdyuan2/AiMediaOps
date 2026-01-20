export type TaskMode = 'standard' | 'interaction' | 'publish';

export interface Task {
  task_id: string;
  account_id: string;
  account_name: string;
  task_type: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'error';
  interval: number;
  valid_time_range: [number, number] | null;
  task_end_time: string;
  last_execution_time: string | null;
  next_execution_time: string | null;
  created_at: string;
  updated_at: string;
  round_num: number | null;
  mode: TaskMode;
  interaction_note_count: number;
  kwargs: Record<string, any>;
  login_status: boolean | null;
  login_status_checked_at: string | null;
}

export interface TaskCreateRequest {
  sys_type: string;
  task_type: string;
  xhs_account_id: string;
  xhs_account_name: string;
  user_query?: string;
  user_topic?: string;
  user_style?: string;
  user_target_audience?: string;
  task_end_time?: string;
  interval?: number;
  valid_time_range?: [number, number] | null;
  mode?: TaskMode;
  interaction_note_count?: number;
}

export interface TaskUpdateRequest {
  user_query?: string;
  user_topic?: string;
  user_style?: string;
  user_target_audience?: string;
  task_end_time?: string;
  interval?: number;
  valid_time_range?: [number, number] | null;
  mode?: TaskMode;
  interaction_note_count?: number;
}

export interface TaskListResponse {
  total: number;
  tasks: Task[];
}

export interface TaskExecuteResponse {
  success: boolean;
  task_id: string;
  message: string;
  execution_start_time?: string;
  execution_end_time?: string;
  duration_seconds?: number;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  module: string;
  function: string;
  message: string;
  task_id?: string;
}

export interface TaskLogsResponse {
  success: boolean;
  task_id: string;
  logs: LogEntry[];
  total: number;
  has_more: boolean;
  message?: string;
}

export interface LoginQrcodeResponse {
  qrcode_base64: string;
  qrcode_url: string;
  timeout?: number;
  message?: string;
}

export interface LoginStatusResponse {
  is_logged_in: boolean;
  message: string;
}

export interface LoginConfirmResponse {
  success: boolean;
  is_logged_in: boolean;
  message: string;
}

export interface ImageInfo {
  filename: string;
  size: number;
  url: string;
}

export interface ImagesListResponse {
  images: ImageInfo[];
}

export interface SourceFileResponse {
  content: string;
  filename: string;
  size?: number;
  modified_time?: string;
}
