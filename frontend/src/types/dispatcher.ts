export interface DispatcherStatus {
  is_running: boolean;
  total_tasks: number;
  pending_tasks: number;
  running_tasks: number;
  paused_tasks: number;
  completed_tasks: number;
  error_tasks: number;
  current_running_task?: {
    task_id: string;
    account_id: string;
    account_name: string;
    started_at: string;
  };
}

export interface APIResponse {
  success: boolean;
  message?: string;
  error?: string;
  data?: any;
}
