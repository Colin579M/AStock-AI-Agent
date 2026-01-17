/**
 * 模式选择页面 - 主页
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { analysisApi } from '../../api/client';
import type { HistoryItem } from '../../api/client';
import './HomePage.css';

export const HomePage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    // 加载历史记录
    analysisApi.getHistory(5).then(setHistory).catch(() => {});
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
          <button className="logout-btn" onClick={logout}>
            退出
          </button>
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
    </div>
  );
};
