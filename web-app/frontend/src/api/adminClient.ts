/**
 * 管理员 API 客户端
 */
import axios from 'axios';

// 生产环境使用相对路径（通过 nginx 代理），开发环境使用 localhost
const API_BASE_URL = import.meta.env.VITE_API_URL === ''
  ? ''
  : (import.meta.env.VITE_API_URL || 'http://localhost:8000');

export const adminApiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加管理员 token
adminApiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('admin_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 处理 401/403
adminApiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('admin_user');
      window.location.href = '/admin/login';
    }
    return Promise.reject(error);
  }
);

// ============== Types ==============

export interface AdminLoginResponse {
  success: boolean;
  token?: string;
  user?: {
    user_id: string;
    name: string;
    role: string;
  };
  message?: string;
}

export interface UserInfo {
  user_id: string;
  name: string;
  role: string;
  expires_at: string | null;
  is_active: boolean;
  created_at: string | null;
  created_by: string | null;
  last_login: string | null;
  login_count: number;
}

export interface CreateUserRequest {
  user_id: string;
  name: string;
  role: 'user' | 'admin';
  expires_at?: string;
  access_code?: string;  // 自定义访问码，留空则自动生成
}

export interface CreateUserResponse {
  success: boolean;
  user_id: string;
  access_code: string;
  message: string;
}

export interface UpdateUserRequest {
  name?: string;
  expires_at?: string;
  is_active?: boolean;
}

export interface SystemStatus {
  backend_status: string;
  chatbot_status: string;
  memory_usage_mb: number;
  memory_percent: number;
  cpu_percent: number;
  active_tasks: number;
  uptime_seconds: number;
}

export interface ApiStats {
  date: string;
  total_requests: number;
  by_endpoint: Record<string, number>;
  by_user: Record<string, number>;
  errors: Record<string, number>;
}

export interface ReportInfo {
  ticker: string;
  date: string;
  report_count: number;
  summary: string;
  path: string;
}

export interface ConversationInfo {
  user_id: string;
  conversation_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminLog {
  id: string;
  timestamp: string;
  admin_id: string;
  action: string;
  target_user_id: string | null;
  details: Record<string, unknown>;
  ip_address: string;
}

export interface ChangelogEntry {
  version: string;
  date: string;
  type: 'feature' | 'improve' | 'fix' | 'breaking';
  title: string;
  description: string;
}

export interface ChangelogData {
  updates: ChangelogEntry[];
}

// ============== Admin API ==============

export const adminApi = {
  // Auth
  login: async (accessCode: string): Promise<AdminLoginResponse> => {
    const response = await adminApiClient.post('/api/auth/login', {
      access_code: accessCode,
    });
    return response.data;
  },

  getCurrentAdmin: async () => {
    const response = await adminApiClient.get('/api/auth/me');
    return response.data;
  },

  // Users
  listUsers: async (): Promise<UserInfo[]> => {
    const response = await adminApiClient.get('/api/admin/users');
    return response.data;
  },

  getUser: async (userId: string): Promise<UserInfo> => {
    const response = await adminApiClient.get(`/api/admin/users/${userId}`);
    return response.data;
  },

  createUser: async (data: CreateUserRequest): Promise<CreateUserResponse> => {
    const response = await adminApiClient.post('/api/admin/users', data);
    return response.data;
  },

  updateUser: async (userId: string, data: UpdateUserRequest): Promise<void> => {
    await adminApiClient.put(`/api/admin/users/${userId}`, data);
  },

  deleteUser: async (userId: string): Promise<void> => {
    await adminApiClient.delete(`/api/admin/users/${userId}`);
  },

  resetUserCode: async (userId: string): Promise<{ success: boolean; access_code: string }> => {
    const response = await adminApiClient.post(`/api/admin/users/${userId}/reset-code`);
    return response.data;
  },

  // System
  getSystemStatus: async (): Promise<SystemStatus> => {
    const response = await adminApiClient.get('/api/admin/stats/system');
    return response.data;
  },

  getApiStats: async (date?: string): Promise<ApiStats> => {
    const url = date ? `/api/admin/stats/api?date=${date}` : '/api/admin/stats/api';
    const response = await adminApiClient.get(url);
    return response.data;
  },

  // Content
  listReports: async (): Promise<ReportInfo[]> => {
    const response = await adminApiClient.get('/api/admin/content/reports');
    return response.data;
  },

  deleteReport: async (ticker: string, date: string): Promise<void> => {
    await adminApiClient.delete(`/api/admin/content/reports/${ticker}/${date}`);
  },

  listConversations: async (): Promise<ConversationInfo[]> => {
    const response = await adminApiClient.get('/api/admin/content/conversations');
    return response.data;
  },

  deleteConversation: async (userId: string, conversationId: string): Promise<void> => {
    await adminApiClient.delete(`/api/admin/content/conversations/${userId}/${conversationId}`);
  },

  // Logs
  getAdminLogs: async (limit = 100, action?: string): Promise<AdminLog[]> => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (action) params.append('action', action);
    const response = await adminApiClient.get(`/api/admin/logs?${params}`);
    return response.data;
  },

  getErrorLogs: async (limit = 100): Promise<Array<{ message: string; level: string }>> => {
    const response = await adminApiClient.get(`/api/admin/logs/errors?limit=${limit}`);
    return response.data;
  },

  // Changelog
  getChangelog: async (): Promise<ChangelogData> => {
    const response = await adminApiClient.get('/api/admin/changelog');
    return response.data;
  },

  updateChangelog: async (data: ChangelogData): Promise<{ success: boolean; message: string }> => {
    const response = await adminApiClient.put('/api/admin/changelog', data);
    return response.data;
  },

  addChangelogEntry: async (entry: ChangelogEntry): Promise<{ success: boolean; message: string }> => {
    const response = await adminApiClient.post('/api/admin/changelog/entry', entry);
    return response.data;
  },

  deleteChangelogEntry: async (version: string): Promise<{ success: boolean; message: string }> => {
    const response = await adminApiClient.delete(`/api/admin/changelog/entry/${encodeURIComponent(version)}`);
    return response.data;
  },
};
