/**
 * 操作日志页面
 */
import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';
import type { AdminLog } from '../../api/adminClient';
import './AdminLogs.css';

const ACTION_LABELS: Record<string, { label: string; color: string }> = {
  user_created: { label: '创建用户', color: 'success' },
  user_updated: { label: '更新用户', color: 'info' },
  user_deleted: { label: '删除用户', color: 'error' },
  code_reset: { label: '重置访问码', color: 'warning' },
  report_deleted: { label: '删除报告', color: 'error' },
  conversation_deleted: { label: '删除对话', color: 'error' },
};

export const AdminLogs: React.FC = () => {
  const [logs, setLogs] = useState<AdminLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterAction, setFilterAction] = useState<string>('');

  // 加载日志
  const loadLogs = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.getAdminLogs(200, filterAction || undefined);
      setLogs(data);
      setError('');
    } catch (err) {
      setError('加载操作日志失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [filterAction]);

  // 格式化时间
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
  };

  // 格式化详情
  const formatDetails = (details: Record<string, unknown>) => {
    if (!details || Object.keys(details).length === 0) return '-';
    return Object.entries(details)
      .map(([key, value]) => `${key}: ${value}`)
      .join(', ');
  };

  // 获取操作标签
  const getActionLabel = (action: string) => {
    return ACTION_LABELS[action] || { label: action, color: 'info' };
  };

  return (
    <div className="admin-logs">
      <div className="admin-page-header">
        <h1>操作日志</h1>
        <p>查看管理员操作历史记录</p>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError('')}>×</button>
        </div>
      )}

      {/* 筛选器 */}
      <div className="logs-filter">
        <select
          className="admin-select"
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
        >
          <option value="">所有操作</option>
          <option value="user_created">创建用户</option>
          <option value="user_updated">更新用户</option>
          <option value="user_deleted">删除用户</option>
          <option value="code_reset">重置访问码</option>
          <option value="report_deleted">删除报告</option>
          <option value="conversation_deleted">删除对话</option>
        </select>

        <button className="admin-btn admin-btn-secondary" onClick={loadLogs}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          刷新
        </button>
      </div>

      {/* 日志列表 */}
      <div className="admin-card">
        {isLoading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>加载中...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="8" y1="6" x2="21" y2="6" />
              <line x1="8" y1="12" x2="21" y2="12" />
              <line x1="8" y1="18" x2="21" y2="18" />
              <line x1="3" y1="6" x2="3.01" y2="6" />
              <line x1="3" y1="12" x2="3.01" y2="12" />
              <line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
            <p>暂无操作记录</p>
          </div>
        ) : (
          <div className="logs-list">
            {logs.map((log) => {
              const actionInfo = getActionLabel(log.action);
              return (
                <div key={log.id} className="log-item">
                  <div className="log-time">{formatTime(log.timestamp)}</div>
                  <div className="log-content">
                    <div className="log-header">
                      <span className={`action-badge action-badge-${actionInfo.color}`}>
                        {actionInfo.label}
                      </span>
                      <span className="log-admin">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                        {log.admin_id}
                      </span>
                      {log.target_user_id && (
                        <span className="log-target">
                          → {log.target_user_id}
                        </span>
                      )}
                    </div>
                    {Object.keys(log.details).length > 0 && (
                      <div className="log-details">{formatDetails(log.details)}</div>
                    )}
                  </div>
                  {log.ip_address && (
                    <div className="log-ip">{log.ip_address}</div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
