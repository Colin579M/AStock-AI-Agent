/**
 * 登录页面 - 开发者工具集首页
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './LoginPage.css';

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

export const LoginPage: React.FC = () => {
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  const [accessCode, setAccessCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showWechat, setShowWechat] = useState(false);
  const [showChangelog, setShowChangelog] = useState(false);
  const [changelog, setChangelog] = useState<ChangelogItem[]>([]);

  const { login } = useAuth();
  const navigate = useNavigate();

  // 加载更新日志（通过 API 获取，避免 CDN 阻止 .json 文件）
  useEffect(() => {
    fetch(`${API_URL}/api/changelog`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        console.log('Changelog data:', data);
        setChangelog(data.updates || []);
      })
      .catch(err => {
        console.error('Changelog fetch error:', err);
        setChangelog([]);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await login(accessCode);
      if (response.success) {
        // 根据选择的工具跳转到不同页面
        if (expandedTool === 'trendradar') {
          navigate('/trendradar', { replace: true });
        } else {
          // 数据查询助手走引导页
          navigate('/guide', { replace: true });
        }
      } else {
        setError(response.message || '访问码错误');
      }
    } catch {
      setError('网络错误，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="dev-portal">
      {/* 微信二维码弹窗 */}
      {showWechat && (
        <div className="wechat-modal" onClick={() => setShowWechat(false)}>
          <div className="wechat-content" onClick={e => e.stopPropagation()}>
            <button className="close-btn" onClick={() => setShowWechat(false)}>×</button>
            <img src="/wechat-qr.jpg" alt="微信二维码" />
            <p>扫码添加微信交流</p>
          </div>
        </div>
      )}

      {/* 更新日志弹窗 */}
      {showChangelog && (
        <div className="changelog-modal" onClick={() => setShowChangelog(false)}>
          <div className="changelog-content" onClick={e => e.stopPropagation()}>
            <div className="changelog-header">
              <h3>📋 更新日志</h3>
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

      {/* 顶部导航 */}
      <header className="portal-header">
        <div className="logo">Colin's Dev Lab</div>
        <div className="header-links">
          <button className="header-link" onClick={() => setShowChangelog(true)}>
            📋 更新日志
          </button>
          <button className="header-link" onClick={() => setShowWechat(true)}>
            💬 联系我
          </button>
        </div>
      </header>

      {/* 主标题 */}
      <section className="hero">
        <h1>👨‍💻 个人开发工具集</h1>
        <p>记录学习，分享交流</p>
      </section>

      {/* 工具卡片 */}
      <div className="tools-grid">
        {/* 数据工具卡片 */}
        <div className={`tool-card ${expandedTool === 'stock' ? 'expanded' : ''}`}>
          <div className="tool-header">
            <span className="tool-icon">📊</span>
            <h2>数据查询助手</h2>
            <span className="beta-tag">Beta v0.2</span>
          </div>
          <p className="tool-desc">
            便捷的数据查询工具，支持公开数据检索与展示。仅供个人学习交流使用。
          </p>
          <div className="tool-tags">
            <span>数据查询</span>
            <span>信息展示</span>
            <span>学习交流</span>
          </div>

          {expandedTool !== 'stock' ? (
            <button className="use-btn" onClick={() => setExpandedTool('stock')}>
              🚀 使用
            </button>
          ) : (
            <form className="login-form" onSubmit={handleSubmit}>
              <div className="input-wrapper">
                <span className="input-icon">🔐</span>
                <input
                  type="password"
                  value={accessCode}
                  onChange={(e) => setAccessCode(e.target.value)}
                  placeholder="输入访问码"
                  disabled={isLoading}
                  autoFocus
                />
              </div>
              {error && <div className="error-msg">{error}</div>}
              <button type="submit" disabled={isLoading || !accessCode}>
                {isLoading ? '验证中...' : '进入 →'}
              </button>
            </form>
          )}
        </div>

        {/* 热点监控卡片 */}
        <div className={`tool-card ${expandedTool === 'trendradar' ? 'expanded' : ''}`}>
          <div className="tool-header">
            <span className="tool-icon">🔥</span>
            <h2>热点监控</h2>
            <span className="beta-tag">Beta v0.2</span>
          </div>
          <p className="tool-desc">
            多平台热点聚合，支持关键词筛选、AI智能分析。实时掌握热点动态。
          </p>
          <div className="tool-tags">
            <span>热点聚合</span>
            <span>AI分析</span>
            <span>实时监控</span>
          </div>

          {expandedTool !== 'trendradar' ? (
            <button className="use-btn" onClick={() => setExpandedTool('trendradar')}>
              🚀 使用
            </button>
          ) : (
            <form className="login-form" onSubmit={handleSubmit}>
              <div className="input-wrapper">
                <span className="input-icon">🔐</span>
                <input
                  type="password"
                  value={accessCode}
                  onChange={(e) => setAccessCode(e.target.value)}
                  placeholder="输入访问码"
                  disabled={isLoading}
                  autoFocus
                />
              </div>
              {error && <div className="error-msg">{error}</div>}
              <button type="submit" disabled={isLoading || !accessCode}>
                {isLoading ? '验证中...' : '进入 →'}
              </button>
            </form>
          )}
        </div>

        {/* 占位卡片 */}
        {[1, 2].map(i => (
          <div key={i} className="tool-card placeholder">
            <div className="tool-header">
              <span className="tool-icon">🚧</span>
              <h2>待开发</h2>
            </div>
            <p className="tool-desc">更多工具开发中，敬请期待...</p>
          </div>
        ))}
      </div>

      {/* 底部声明 */}
      <footer className="portal-footer">
        <p>⚠️ 个人学习项目 · 仅供个人使用 · 不对外开放</p>
        <a href="https://beian.miit.gov.cn" target="_blank" rel="noopener noreferrer" className="icp-link">
          辽ICP备2026001015号-1
        </a>
      </footer>
    </div>
  );
};
