/**
 * 模式选择页面 - 主页
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { analysisApi } from '../../api/client';
import type { HistoryItem } from '../../api/client';
import './HomePage.css';

const API_URL = import.meta.env.VITE_API_URL === ''
  ? ''
  : (import.meta.env.VITE_API_URL || 'http://localhost:8000');

interface ChangelogItem {
  version: string;
  date: string;
  type: 'feature' | 'improve' | 'fix' | 'breaking';
  title: string;
  description: string;
}

const TYPE_LABELS: Record<string, string> = {
  feature: '新功能',
  improve: '优化',
  fix: '修复',
  breaking: '重大变更'
};

export const HomePage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showChangelog, setShowChangelog] = useState(false);
  const [changelog, setChangelog] = useState<ChangelogItem[]>([]);

  useEffect(() => {
    // 加载历史记录
    analysisApi.getHistory(5).then(setHistory).catch(() => {});
  }, []);

  // 加载更新日志
  useEffect(() => {
    fetch(`${API_URL}/api/changelog`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        setChangelog(data.updates || []);
      })
      .catch(err => {
        console.error('Changelog fetch error:', err);
        setChangelog([]);
      });
  }, []);

  const getDecisionColor = (decision?: string) => {
    if (!decision) return '#666';
    const d = decision.toLowerCase();
    if (d.includes('买') || d.includes('buy')) return '#22c55e';
    if (d.includes('卖') || d.includes('sell')) return '#ef4444';
    return '#f59e0b';
  };

  return (
    <div className="home-page">
      <header className="home-header">
        <div className="home-header-inner">
          <div className="home-header-text">
            <h1>股票分析助手</h1>
            <p className="welcome-text">欢迎回来，{user?.name}</p>
          </div>
          <div className="header-actions">
            <button className="changelog-btn" onClick={(e) => { e.stopPropagation(); setShowChangelog(true); }}>
              更新日志
            </button>
            <button className="logout-btn" onClick={logout}>
              退出
            </button>
          </div>
        </div>
      </header>

      <main className="home-content">
        {/* 全面分析卡片 */}
        <div className="mode-card analysis-mode" onClick={() => navigate('/analysis')}>
          <div className="mode-icon">📊</div>
          <div className="mode-info">
            <h2>全面分析报告</h2>
            <p className="mode-desc">11个AI专家协作</p>
            <ul className="mode-features">
              <li>技术面分析</li>
              <li>基本面分析</li>
              <li>情绪面分析</li>
              <li>综合投资建议</li>
            </ul>
            <p className="mode-time">约5-10分钟</p>
          </div>
          <button className="mode-btn primary">开始分析</button>
        </div>

        {/* 对话模式卡片 */}
        <div className="mode-card chat-mode" onClick={() => navigate('/chat')}>
          <div className="mode-icon">💬</div>
          <div className="mode-info">
            <h2>智能对话</h2>
            <p className="mode-desc">随时问答，快速响应</p>
            <ul className="mode-features">
              <li>查价格、估值</li>
              <li>问基本面、趋势</li>
              <li>多轮对话支持</li>
            </ul>
          </div>
          <button className="mode-btn">进入对话</button>
        </div>
      </main>

      {/* 历史记录 - 始终显示 */}
      <section className="history-section">
        <div className="history-header">
          <h3>历史报告 ({history.length}份)</h3>
          <button className="view-all-btn" onClick={() => navigate('/history')}>
            查看全部 →
          </button>
        </div>
        {history.length > 0 ? (
          <ul className="history-list">
            {history.map((item) => (
              <li
                key={item.task_id}
                className="history-item"
                onClick={() => {
                  if (item.status === 'completed') {
                    navigate(`/analysis/result/${item.task_id}`);
                  } else if (item.status === 'running' || item.status === 'pending') {
                    navigate(`/analysis/${item.task_id}`);
                  }
                }}
              >
                <span className="history-ticker">
                  {item.ticker.split('.')[0]}
                </span>
                <span className="history-name">{item.ticker_name}</span>
                <span
                  className="history-decision"
                  style={{ color: getDecisionColor(item.decision) }}
                >
                  {item.decision || item.status}
                </span>
                <span className="history-date">
                  {item.date.substring(5)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="history-empty">
            <span>暂无本次会话的分析记录</span>
          </div>
        )}
      </section>

      {/* 更新日志 Modal */}
      {showChangelog && (
        <div className="changelog-modal" onClick={() => setShowChangelog(false)}>
          <div className="changelog-content" onClick={e => e.stopPropagation()}>
            <div className="changelog-header">
              <h3>更新日志</h3>
              <button className="close-btn" onClick={() => setShowChangelog(false)}>×</button>
            </div>
            <div className="changelog-list">
              {changelog.map((item, index) => (
                <div key={index} className="changelog-item">
                  <div className="changelog-item-header">
                    <span className={`changelog-tag ${item.type}`}>
                      {TYPE_LABELS[item.type] || item.type}
                    </span>
                    <span className="changelog-version">{item.version}</span>
                    <span className="changelog-date">{item.date}</span>
                  </div>
                  <div className="changelog-item-title">{item.title}</div>
                  <div className="changelog-item-desc">{item.description}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
