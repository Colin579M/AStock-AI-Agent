/**
 * 内容管理页面
 */
import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';
import type { ReportInfo, ConversationInfo } from '../../api/adminClient';
import './ContentManagement.css';

type TabType = 'reports' | 'conversations';

export const ContentManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('reports');
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // 加载数据
  const loadData = async () => {
    try {
      setIsLoading(true);
      if (activeTab === 'reports') {
        const data = await adminApi.listReports();
        setReports(data);
      } else {
        const data = await adminApi.listConversations();
        setConversations(data);
      }
      setError('');
    } catch (err) {
      setError('加载数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeTab]);

  // 删除报告
  const handleDeleteReport = async (ticker: string, date: string) => {
    if (!confirm(`确定要删除 ${ticker} (${date}) 的分析报告吗？此操作不可撤销。`)) {
      return;
    }

    try {
      await adminApi.deleteReport(ticker, date);
      loadData();
    } catch (err) {
      setError('删除报告失败');
    }
  };

  // 删除对话
  const handleDeleteConversation = async (userId: string, conversationId: string) => {
    if (!confirm(`确定要删除该对话吗？此操作不可撤销。`)) {
      return;
    }

    try {
      await adminApi.deleteConversation(userId, conversationId);
      loadData();
    } catch (err) {
      setError('删除对话失败');
    }
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  return (
    <div className="content-management">
      <div className="admin-page-header">
        <h1>内容管理</h1>
        <p>管理分析报告和对话记录</p>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError('')}>×</button>
        </div>
      )}

      {/* 标签页 */}
      <div className="content-tabs">
        <button
          className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          分析报告
          <span className="tab-count">{reports.length}</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'conversations' ? 'active' : ''}`}
          onClick={() => setActiveTab('conversations')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          对话记录
          <span className="tab-count">{conversations.length}</span>
        </button>
      </div>

      {/* 内容区 */}
      <div className="admin-card">
        {isLoading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>加载中...</p>
          </div>
        ) : activeTab === 'reports' ? (
          // 报告列表
          reports.length === 0 ? (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <p>暂无分析报告</p>
            </div>
          ) : (
            <div className="content-list">
              {reports.map((report) => (
                <div key={`${report.ticker}-${report.date}`} className="content-item">
                  <div className="content-info">
                    <div className="content-title">
                      <span className="ticker-badge">{report.ticker}</span>
                      <span className="content-date">{report.date}</span>
                    </div>
                    <div className="content-meta">
                      <span>{report.report_count} 份报告</span>
                    </div>
                    {report.summary && (
                      <div className="content-summary">{report.summary}</div>
                    )}
                  </div>
                  <div className="content-actions">
                    <button
                      className="admin-btn admin-btn-danger admin-btn-icon"
                      onClick={() => handleDeleteReport(report.ticker, report.date)}
                      title="删除报告"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          // 对话列表
          conversations.length === 0 ? (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <p>暂无对话记录</p>
            </div>
          ) : (
            <div className="content-list">
              {conversations.map((conv) => (
                <div key={`${conv.user_id}-${conv.conversation_id}`} className="content-item">
                  <div className="content-info">
                    <div className="content-title">
                      <span className="user-badge">{conv.user_id}</span>
                      <span className="content-date">{conv.title}</span>
                    </div>
                    <div className="content-meta">
                      <span>{conv.message_count} 条消息</span>
                      <span>·</span>
                      <span>更新于 {formatDate(conv.updated_at)}</span>
                    </div>
                  </div>
                  <div className="content-actions">
                    <button
                      className="admin-btn admin-btn-danger admin-btn-icon"
                      onClick={() => handleDeleteConversation(conv.user_id, conv.conversation_id)}
                      title="删除对话"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
};
