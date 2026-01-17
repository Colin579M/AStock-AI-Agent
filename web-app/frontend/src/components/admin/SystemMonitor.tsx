/**
 * 系统监控页面
 */
import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';
import type { SystemStatus, ApiStats } from '../../api/adminClient';
import './SystemMonitor.css';

export const SystemMonitor: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [apiStats, setApiStats] = useState<ApiStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // 加载数据
  const loadData = async () => {
    try {
      setIsLoading(true);
      const [status, stats] = await Promise.all([
        adminApi.getSystemStatus(),
        adminApi.getApiStats(),
      ]);
      setSystemStatus(status);
      setApiStats(stats);
      setError('');
    } catch (err) {
      setError('加载系统状态失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // 每 30 秒刷新
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  // 格式化运行时间
  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}天 ${hours}小时`;
    if (hours > 0) return `${hours}小时 ${minutes}分钟`;
    return `${minutes}分钟`;
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'ready':
        return 'success';
      case 'degraded':
      case 'loading':
        return 'warning';
      default:
        return 'error';
    }
  };

  // 获取状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy':
        return '正常';
      case 'ready':
        return '就绪';
      case 'degraded':
        return '降级';
      case 'loading':
        return '加载中';
      case 'not_loaded':
        return '未加载';
      case 'error':
        return '错误';
      default:
        return status;
    }
  };

  if (isLoading && !systemStatus) {
    return (
      <div className="system-monitor">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>加载系统状态...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="system-monitor">
      <div className="admin-page-header">
        <h1>系统监控</h1>
        <p>实时监控系统运行状态和 API 使用情况</p>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError('')}>×</button>
        </div>
      )}

      {/* 状态卡片 */}
      <div className="status-cards">
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-icon backend">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                <line x1="6" y1="6" x2="6.01" y2="6" />
                <line x1="6" y1="18" x2="6.01" y2="18" />
              </svg>
            </span>
            <span className="status-card-title">后端服务</span>
          </div>
          <div className="status-card-value">
            <span className={`status-badge status-badge-${getStatusColor(systemStatus?.backend_status || '')}`}>
              {getStatusText(systemStatus?.backend_status || '')}
            </span>
          </div>
          <div className="status-card-detail">
            运行时间: {formatUptime(systemStatus?.uptime_seconds || 0)}
          </div>
        </div>

        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-icon chatbot">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </span>
            <span className="status-card-title">Chatbot</span>
          </div>
          <div className="status-card-value">
            <span className={`status-badge status-badge-${getStatusColor(systemStatus?.chatbot_status || '')}`}>
              {getStatusText(systemStatus?.chatbot_status || '')}
            </span>
          </div>
          <div className="status-card-detail">
            活跃任务: {systemStatus?.active_tasks || 0}
          </div>
        </div>

        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-icon memory">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
                <rect x="9" y="9" width="6" height="6" />
                <line x1="9" y1="1" x2="9" y2="4" />
                <line x1="15" y1="1" x2="15" y2="4" />
                <line x1="9" y1="20" x2="9" y2="23" />
                <line x1="15" y1="20" x2="15" y2="23" />
                <line x1="20" y1="9" x2="23" y2="9" />
                <line x1="20" y1="14" x2="23" y2="14" />
                <line x1="1" y1="9" x2="4" y2="9" />
                <line x1="1" y1="14" x2="4" y2="14" />
              </svg>
            </span>
            <span className="status-card-title">内存使用</span>
          </div>
          <div className="status-card-value">
            {systemStatus?.memory_usage_mb?.toFixed(0) || 0} MB
          </div>
          <div className="status-card-detail">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${Math.min(systemStatus?.memory_percent || 0, 100)}%` }}
              />
            </div>
            <span>{systemStatus?.memory_percent?.toFixed(1) || 0}%</span>
          </div>
        </div>

        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-icon cpu">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </span>
            <span className="status-card-title">CPU 使用</span>
          </div>
          <div className="status-card-value">
            {systemStatus?.cpu_percent?.toFixed(1) || 0}%
          </div>
          <div className="status-card-detail">
            <div className="progress-bar">
              <div
                className="progress-fill cpu-fill"
                style={{ width: `${Math.min(systemStatus?.cpu_percent || 0, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* API 统计 */}
      <div className="admin-card">
        <div className="admin-card-header">
          <h2 className="admin-card-title">今日 API 统计</h2>
          <span className="stats-date">{apiStats?.date}</span>
        </div>

        <div className="stats-grid">
          <div className="stats-item">
            <div className="stats-value">{apiStats?.total_requests || 0}</div>
            <div className="stats-label">总请求数</div>
          </div>
          <div className="stats-item">
            <div className="stats-value">{Object.keys(apiStats?.by_user || {}).length}</div>
            <div className="stats-label">活跃用户</div>
          </div>
          <div className="stats-item">
            <div className="stats-value error">
              {Object.values(apiStats?.errors || {}).reduce((a, b) => a + b, 0)}
            </div>
            <div className="stats-label">错误数</div>
          </div>
        </div>

        {/* 端点统计 */}
        {apiStats && Object.keys(apiStats.by_endpoint).length > 0 && (
          <div className="endpoint-stats">
            <h3>端点统计</h3>
            <div className="endpoint-list">
              {Object.entries(apiStats.by_endpoint)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([endpoint, count]) => (
                  <div key={endpoint} className="endpoint-item">
                    <span className="endpoint-name">{endpoint}</span>
                    <span className="endpoint-count">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* 用户统计 */}
        {apiStats && Object.keys(apiStats.by_user).length > 0 && (
          <div className="user-stats">
            <h3>用户请求统计</h3>
            <div className="user-list">
              {Object.entries(apiStats.by_user)
                .sort((a, b) => b[1] - a[1])
                .map(([user, count]) => (
                  <div key={user} className="user-item">
                    <span className="user-name">{user}</span>
                    <span className="user-count">{count} 次</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* 刷新按钮 */}
      <div className="refresh-section">
        <button className="admin-btn admin-btn-secondary" onClick={loadData} disabled={isLoading}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          {isLoading ? '刷新中...' : '刷新数据'}
        </button>
        <span className="refresh-hint">每 30 秒自动刷新</span>
      </div>
    </div>
  );
};
