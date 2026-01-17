/**
 * API 客户端配置
 */
import axios from 'axios';

// 生产环境使用相对路径（通过 nginx 代理），开发环境使用 localhost
const API_BASE_URL = import.meta.env.VITE_API_URL === ''
  ? ''  // 空字符串 = 使用相对路径，nginx 会代理 /api 到后端
  : (import.meta.env.VITE_API_URL || 'http://localhost:8000');

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 处理 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============== Auth API ==============

export interface LoginResponse {
  success: boolean;
  token?: string;
  user?: {
    user_id: string;
    name: string;
    expires_at: string | null;
  };
  is_first_login?: boolean;
  message?: string;
}

export const authApi = {
  login: async (accessCode: string): Promise<LoginResponse> => {
    const response = await apiClient.post('/api/auth/login', {
      access_code: accessCode,
    });
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/api/auth/me');
    return response.data;
  },

  logout: async () => {
    await apiClient.post('/api/auth/logout');
  },
};

// ============== Chat API ==============

export interface ChatResponse {
  response: string;
  query_type: string;
  conversation_id: string;
}

export interface Conversation {
  conversation_id: string;
  title: string;
  last_message: string;
  updated_at: string;
  message_count: number;
}

export const chatApi = {
  sendMessage: async (
    message: string,
    conversationId?: string
  ): Promise<ChatResponse> => {
    const response = await apiClient.post('/api/chat/message', {
      message,
      conversation_id: conversationId,
    });
    return response.data;
  },

  getConversations: async (): Promise<Conversation[]> => {
    const response = await apiClient.get('/api/chat/conversations');
    return response.data.conversations;
  },

  getConversation: async (conversationId: string) => {
    const response = await apiClient.get(
      `/api/chat/conversations/${conversationId}`
    );
    return response.data;
  },

  deleteConversation: async (conversationId: string) => {
    await apiClient.delete(`/api/chat/conversations/${conversationId}`);
  },
};

// ============== Analysis API ==============

export interface AnalysisProgress {
  current_step: string | null;
  current_step_name: string | null;
  completed_steps: string[];
  total_steps: number;
  active_analysts?: Array<{ key: string; status: string; name?: string }>;
}

export interface TaskStatus {
  task_id: string;
  ticker: string;
  ticker_name: string;
  date: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: AnalysisProgress;
  logs: string[];
  error?: string;
  created_at: string;
  completed_at?: string;
}

export interface AnalysisResult {
  ticker: string;
  signal: string;
  decision: string;
  summary?: {
    decision?: string;
    target_price?: number;
    confidence?: number;
  };
  reports: Record<
    string,
    {
      name: string;
      content: string;
    }
  >;
}

export interface HistoryItem {
  task_id: string;
  ticker: string;
  ticker_name: string;
  date: string;
  status: string;
  decision?: string;
  created_at: string;
  completed_at?: string;
}

export const analysisApi = {
  startAnalysis: async (
    ticker: string,
    tickerName?: string,
    date?: string
  ): Promise<{ success: boolean; task_id: string; message: string }> => {
    const response = await apiClient.post('/api/analysis/run', {
      ticker,
      ticker_name: tickerName,
      date,
    });
    return response.data;
  },

  getTaskStatus: async (taskId: string): Promise<TaskStatus> => {
    const response = await apiClient.get(`/api/analysis/status/${taskId}`);
    return response.data;
  },

  getTaskResult: async (
    taskId: string
  ): Promise<{ success: boolean } & AnalysisResult> => {
    const response = await apiClient.get(`/api/analysis/result/${taskId}`);
    return response.data;
  },

  getHistory: async (limit = 10): Promise<HistoryItem[]> => {
    const response = await apiClient.get(`/api/analysis/history?limit=${limit}`);
    return response.data.history;
  },

  cancelTask: async (taskId: string) => {
    await apiClient.delete(`/api/analysis/${taskId}`);
  },

  getIntermediateReport: async (
    taskId: string,
    reportType: string
  ): Promise<{ success: boolean; report_type: string; report_name: string; content: string }> => {
    const response = await apiClient.get(`/api/analysis/${taskId}/report/${reportType}`);
    return response.data;
  },

  // 历史报告浏览 API
  browseAllStocks: async (): Promise<{
    success: boolean;
    count: number;
    stocks: Array<{ ticker: string; latest_date: string; report_count: number }>;
  }> => {
    const response = await apiClient.get('/api/analysis/history/browse');
    return response.data;
  },

  getStockReportDates: async (ticker: string): Promise<{
    success: boolean;
    ticker: string;
    count: number;
    dates: Array<{ date: string; has_summary: boolean; reports: string[] }>;
  }> => {
    const response = await apiClient.get(`/api/analysis/history/stock/${ticker}`);
    return response.data;
  },

  getHistoricalReport: async (
    ticker: string,
    date: string,
    reportType: string = 'final_report'
  ): Promise<{
    success: boolean;
    ticker: string;
    date: string;
    report_type: string;
    report_name: string;
    content: string;
    summary?: Record<string, unknown>;
  }> => {
    const response = await apiClient.get(
      `/api/analysis/history/stock/${ticker}/${date}?report_type=${reportType}`
    );
    return response.data;
  },
};

// ============== TrendRadar API ==============

export interface Platform {
  id: string;
  name: string;
}

export interface HotItem {
  rank: number;
  title: string;
  url: string;
  mobile_url?: string;
  hot?: string;
}

export interface PlatformData {
  platform_id: string;
  platform_name: string;
  success: boolean;
  error?: string;
  items: HotItem[];
  count: number;
  cached?: boolean;
}

export interface AnalyzeRequest {
  platform_ids?: string[];
  keywords?: string[];
  include_rss?: boolean;
  max_news?: number;
}

export interface AIAnalysisResult {
  success: boolean;
  summary?: string;
  keyword_analysis?: string;
  sentiment?: string;
  cross_platform?: string;
  signals?: string;
  conclusion?: string;
  stats?: {
    total_news: number;
    analyzed_news: number;
    hotlist_count: number;
    rss_count: number;
  };
  error?: string;
  from_cache?: boolean;
}

export interface RSSFeed {
  id: string;
  name: string;
  url: string;
  enabled: boolean;
  max_age_days: number;
  is_default: boolean;
}

export interface RSSItem {
  feed_id: string;
  feed_name: string;
  title: string;
  url: string;
  summary?: string;
  published?: string;
}

export const trendradarApi = {
  // 获取平台列表
  getPlatforms: async (): Promise<{ success: boolean; platforms: Platform[] }> => {
    const response = await apiClient.get('/api/trendradar/platforms');
    return response.data;
  },

  // 获取热榜数据
  getHotlist: async (
    platformIds?: string[],
    refresh = false
  ): Promise<{
    success: boolean;
    platforms: Record<string, PlatformData>;
    summary: { total: number; success: number; failed: number };
  }> => {
    const params = new URLSearchParams();
    if (platformIds && platformIds.length > 0) {
      params.append('platforms', platformIds.join(','));
    }
    if (refresh) {
      params.append('refresh', 'true');
    }
    const response = await apiClient.get(`/api/trendradar/hotlist?${params}`);
    return response.data;
  },

  // 获取单个平台热榜
  getSingleHotlist: async (
    platformId: string,
    refresh = false
  ): Promise<PlatformData> => {
    const params = refresh ? '?refresh=true' : '';
    const response = await apiClient.get(`/api/trendradar/hotlist/${platformId}${params}`);
    return response.data;
  },

  // 关键词相关
  getKeywords: async (): Promise<{ success: boolean; keywords: string[] }> => {
    const response = await apiClient.get('/api/trendradar/keywords');
    return response.data;
  },

  setKeywords: async (keywords: string[]): Promise<{ success: boolean; keywords: string[] }> => {
    const response = await apiClient.post('/api/trendradar/keywords', { keywords });
    return response.data;
  },

  // 筛选热榜
  filterHotlist: async (
    platformIds?: string[],
    keywords?: string[]
  ): Promise<{
    success: boolean;
    platforms: Record<string, PlatformData>;
    keywords_used?: string[];
  }> => {
    const response = await apiClient.post('/api/trendradar/filter', {
      platform_ids: platformIds,
      keywords,
    });
    return response.data;
  },

  // RSS 相关
  getRSSFeeds: async (): Promise<{ success: boolean; feeds: RSSFeed[] }> => {
    const response = await apiClient.get('/api/trendradar/rss/feeds');
    return response.data;
  },

  getRSSItems: async (
    feedIds?: string[]
  ): Promise<{
    success: boolean;
    items: RSSItem[];
    count: number;
    errors?: Array<{ feed_id: string; error: string }>;
  }> => {
    const params = feedIds ? `?feeds=${feedIds.join(',')}` : '';
    const response = await apiClient.get(`/api/trendradar/rss/items${params}`);
    return response.data;
  },

  addRSSFeed: async (
    feedId: string,
    name: string,
    url: string,
    maxAgeDays = 3
  ): Promise<{ success: boolean; feed?: { id: string; name: string; url: string }; error?: string }> => {
    const response = await apiClient.post('/api/trendradar/rss/subscribe', {
      feed_id: feedId,
      name,
      url,
      max_age_days: maxAgeDays,
    });
    return response.data;
  },

  removeRSSFeed: async (feedId: string): Promise<{ success: boolean; error?: string }> => {
    const response = await apiClient.delete(`/api/trendradar/rss/unsubscribe/${feedId}`);
    return response.data;
  },

  // AI 分析
  analyze: async (request: AnalyzeRequest): Promise<AIAnalysisResult> => {
    const response = await apiClient.post('/api/trendradar/analyze', request);
    return response.data;
  },

  // 清空缓存（管理员）
  clearCache: async (): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post('/api/trendradar/cache/clear');
    return response.data;
  },
};
