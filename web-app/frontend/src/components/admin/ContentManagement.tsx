/**
 * 内容管理页面
 */
import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';
import type { ReportInfo, ConversationInfo, ChangelogEntry } from '../../api/adminClient';
import './ContentManagement.css';

type TabType = 'reports' | 'conversations' | 'changelog';

const TYPE_LABELS: Record<ChangelogEntry['type'], { label: string; color: string }> = {
  feature: { label: '新功能', color: '#10b981' },
  improve: { label: '优化', color: '#3b82f6' },
  fix: { label: '修复', color: '#f59e0b' },
  breaking: { label: '重大变更', color: '#ef4444' },
};

export const ContentManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('reports');
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [changelog, setChangelog] = useState<ChangelogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Changelog 编辑状态
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingEntry, setEditingEntry] = useState<ChangelogEntry | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);  // 用索引追踪，避免version重复问题
  const [formData, setFormData] = useState<ChangelogEntry>({
    version: '',
    date: new Date().toISOString().split('T')[0],
    type: 'feature',
    title: '',
    description: '',
  });

  // 加载数据
  const loadData = async () => {
    try {
      setIsLoading(true);
      if (activeTab === 'reports') {
        const data = await adminApi.listReports();
        setReports(data);
      } else if (activeTab === 'conversations') {
        const data = await adminApi.listConversations();
        setConversations(data);
      } else if (activeTab === 'changelog') {
        const data = await adminApi.getChangelog();
        setChangelog(data.updates || []);
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

  // Changelog 操作
  const handleAddChangelog = async () => {
    if (!formData.version || !formData.title) {
      setError('请填写版本号和标题');
      return;
    }

    try {
      await adminApi.addChangelogEntry(formData);
      setShowAddForm(false);
      setFormData({
        version: '',
        date: new Date().toISOString().split('T')[0],
        type: 'feature',
        title: '',
        description: '',
      });
      loadData();
    } catch (err) {
      setError('添加更新日志失败');
    }
  };

  const handleDeleteChangelog = async (index: number, version: string) => {
    if (!confirm(`确定要删除版本 ${version} 的更新日志吗？`)) {
      return;
    }

    try {
      // 用索引删除，避免version重复导致删错条目
      const newChangelog = changelog.filter((_, i) => i !== index);
      await adminApi.updateChangelog({ updates: newChangelog });
      loadData();
    } catch (err) {
      setError('删除更新日志失败');
    }
  };

  const handleEditChangelog = (entry: ChangelogEntry, index: number) => {
    setEditingEntry(entry);
    setEditingIndex(index);
    setFormData({ ...entry });
  };

  const handleSaveEdit = async () => {
    if (!editingEntry || editingIndex === null) return;

    try {
      // 使用索引更新，避免version重复导致多条被修改
      const newChangelog = changelog.map((e, i) =>
        i === editingIndex ? formData : e
      );
      await adminApi.updateChangelog({ updates: newChangelog });
      setEditingEntry(null);
      setEditingIndex(null);
      setFormData({
        version: '',
        date: new Date().toISOString().split('T')[0],
        type: 'feature',
        title: '',
        description: '',
      });
      loadData();
    } catch (err) {
      setError('保存更新日志失败');
    }
  };

  const handleCancelEdit = () => {
    setEditingEntry(null);
    setEditingIndex(null);
    setShowAddForm(false);
    setFormData({
      version: '',
      date: new Date().toISOString().split('T')[0],
      type: 'feature',
      title: '',
      description: '',
    });
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  // 渲染 Changelog 表单
  const renderChangelogForm = () => (
    <div className="changelog-form">
      <div className="form-row">
        <div className="form-group">
          <label>版本号</label>
          <input
            type="text"
            value={formData.version}
            onChange={(e) => setFormData({ ...formData, version: e.target.value })}
            placeholder="如 v0.1.14"
          />
        </div>
        <div className="form-group">
          <label>日期</label>
          <input
            type="date"
            value={formData.date}
            onChange={(e) => setFormData({ ...formData, date: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>类型</label>
          <select
            value={formData.type}
            onChange={(e) => setFormData({ ...formData, type: e.target.value as ChangelogEntry['type'] })}
          >
            <option value="feature">新功能</option>
            <option value="improve">优化</option>
            <option value="fix">修复</option>
            <option value="breaking">重大变更</option>
          </select>
        </div>
      </div>
      <div className="form-group">
        <label>标题</label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          placeholder="简短描述本次更新"
        />
      </div>
      <div className="form-group">
        <label>详细说明</label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="详细描述更新内容..."
          rows={3}
        />
      </div>
      <div className="form-actions">
        <button className="admin-btn admin-btn-secondary" onClick={handleCancelEdit}>
          取消
        </button>
        <button
          className="admin-btn admin-btn-primary"
          onClick={editingEntry ? handleSaveEdit : handleAddChangelog}
        >
          {editingEntry ? '保存修改' : '添加'}
        </button>
      </div>
    </div>
  );

  return (
    <div className="content-management">
      <div className="admin-page-header">
        <h1>内容管理</h1>
        <p>管理分析报告、对话记录和更新日志</p>
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
        <button
          className={`tab-btn ${activeTab === 'changelog' ? 'active' : ''}`}
          onClick={() => setActiveTab('changelog')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 8v4l3 3" />
            <circle cx="12" cy="12" r="10" />
          </svg>
          更新日志
          <span className="tab-count">{changelog.length}</span>
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
        ) : activeTab === 'conversations' ? (
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
        ) : (
          // Changelog 列表
          <div className="changelog-management">
            {/* 添加按钮 */}
            {!showAddForm && !editingEntry && (
              <button
                className="admin-btn admin-btn-primary add-changelog-btn"
                onClick={() => setShowAddForm(true)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                添加更新日志
              </button>
            )}

            {/* 添加/编辑表单 */}
            {(showAddForm || editingEntry) && renderChangelogForm()}

            {/* Changelog 列表 */}
            {changelog.length === 0 ? (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 8v4l3 3" />
                  <circle cx="12" cy="12" r="10" />
                </svg>
                <p>暂无更新日志</p>
              </div>
            ) : (
              <div className="content-list changelog-list">
                {changelog.map((entry, index) => (
                  <div key={`${entry.version}-${index}`} className="content-item changelog-item">
                    <div className="content-info">
                      <div className="content-title">
                        <span
                          className="type-badge"
                          style={{ backgroundColor: TYPE_LABELS[entry.type].color }}
                        >
                          {TYPE_LABELS[entry.type].label}
                        </span>
                        <span className="version-badge">{entry.version}</span>
                        <span className="content-date">{entry.date}</span>
                      </div>
                      <div className="changelog-title">{entry.title}</div>
                      {entry.description && (
                        <div className="content-summary">{entry.description}</div>
                      )}
                    </div>
                    <div className="content-actions">
                      <button
                        className="admin-btn admin-btn-secondary admin-btn-icon"
                        onClick={() => handleEditChangelog(entry, index)}
                        title="编辑"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      <button
                        className="admin-btn admin-btn-danger admin-btn-icon"
                        onClick={() => handleDeleteChangelog(index, entry.version)}
                        title="删除"
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
            )}
          </div>
        )}
      </div>
    </div>
  );
};
