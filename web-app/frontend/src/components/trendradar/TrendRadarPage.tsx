/**
 * TrendRadar 热点监控页面
 *
 * 功能：
 * - 多平台热榜浏览
 * - 关键词筛选
 * - AI 智能分析
 * - RSS 订阅管理
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { trendradarApi } from '../../api/client';
import './TrendRadarPage.css';

interface Platform {
  id: string;
  name: string;
}

interface HotItem {
  rank: number;
  title: string;
  url: string;
  mobile_url?: string;
  hot?: string;
}

interface PlatformData {
  platform_id: string;
  platform_name: string;
  success: boolean;
  error?: string;
  items: HotItem[];
  count: number;
  cached?: boolean;
}

interface AIAnalysisResult {
  success: boolean;
  summary?: string | string[];
  keyword_analysis?: string | string[];
  sentiment?: string | string[];
  cross_platform?: string | string[];
  signals?: string | string[];
  conclusion?: string | string[];
  stats?: {
    total_news: number;
    analyzed_news: number;
    hotlist_count: number;
    rss_count: number;
  };
  error?: string;
  from_cache?: boolean;
}

// 安全地将任意类型转换为可显示的字符串
const safeRenderText = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.join('\n');
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

// 简单的 Markdown 渲染（支持加粗、斜体、列表）
const renderMarkdown = (text: string): React.ReactNode => {
  // 将文本按行分割处理
  const lines = text.split('\n');

  const processLine = (line: string): React.ReactNode => {
    // 处理加粗 **text** 或 __text__
    let processed = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    processed = processed.replace(/__(.+?)__/g, '<strong>$1</strong>');
    // 处理斜体 *text* 或 _text_
    processed = processed.replace(/\*([^*]+?)\*/g, '<em>$1</em>');
    processed = processed.replace(/_([^_]+?)_/g, '<em>$1</em>');
    // 处理行内代码 `code`
    processed = processed.replace(/`([^`]+?)`/g, '<code>$1</code>');

    return <span dangerouslySetInnerHTML={{ __html: processed }} />;
  };

  return (
    <div className="markdown-content">
      {lines.map((line, index) => {
        // 处理有序列表 (1. 2. 等)
        const orderedMatch = line.match(/^(\d+)\.\s+(.+)$/);
        if (orderedMatch) {
          return (
            <div key={index} className="md-list-item">
              <span className="md-list-number">{orderedMatch[1]}.</span>
              <span className="md-list-content">{processLine(orderedMatch[2])}</span>
            </div>
          );
        }
        // 处理无序列表 (- 或 *)
        const unorderedMatch = line.match(/^[-*]\s+(.+)$/);
        if (unorderedMatch) {
          return (
            <div key={index} className="md-list-item">
              <span className="md-list-bullet">•</span>
              <span className="md-list-content">{processLine(unorderedMatch[1])}</span>
            </div>
          );
        }
        // 空行
        if (line.trim() === '') {
          return <div key={index} className="md-spacer" />;
        }
        // 普通段落
        return <div key={index} className="md-paragraph">{processLine(line)}</div>;
      })}
    </div>
  );
};

// 渲染分析内容（支持 Markdown）
const renderAnalysisContent = (value: unknown): React.ReactNode => {
  const text = safeRenderText(value);
  return renderMarkdown(text);
};

// 渲染关键词分析表格
const renderKeywordTable = (value: unknown): React.ReactNode => {
  // 如果是对象格式（分类 -> 关键词数组）
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const categories = Object.entries(value as Record<string, unknown>);
    if (categories.length > 0) {
      return (
        <table className="keyword-table">
          <thead>
            <tr>
              <th>分类</th>
              <th>关键词</th>
            </tr>
          </thead>
          <tbody>
            {categories.map(([category, keywords]) => (
              <tr key={category}>
                <td className="category-cell">{category}</td>
                <td className="keywords-cell">
                  {Array.isArray(keywords)
                    ? keywords.map((kw, i) => (
                        <span key={i} className="keyword-badge">{String(kw)}</span>
                      ))
                    : String(keywords)
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
  }
  // 降级为文本显示
  return <pre className="analysis-text">{safeRenderText(value)}</pre>;
};

export const TrendRadarPage: React.FC = () => {
  const navigate = useNavigate();
  useAuth(); // 确保已登录

  // 状态
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [hotlistData, setHotlistData] = useState<Record<string, PlatformData>>({});
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AIAnalysisResult | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [error, setError] = useState('');

  // 加载平台列表
  useEffect(() => {
    loadPlatforms();
  }, []);

  const loadPlatforms = async () => {
    try {
      const data = await trendradarApi.getPlatforms();
      if (data.success) {
        setPlatforms(data.platforms);
        // 默认选中前 5 个平台
        const defaultSelected = data.platforms.slice(0, 5).map((p: Platform) => p.id);
        setSelectedPlatforms(defaultSelected);
      }
    } catch (err) {
      console.error('加载平台失败:', err);
      setError('加载平台列表失败');
    }
  };

  // 加载热榜数据
  const loadHotlist = useCallback(async (refresh = false) => {
    if (selectedPlatforms.length === 0) return;

    setLoading(true);
    setError('');

    try {
      const data = await trendradarApi.getHotlist(selectedPlatforms, refresh);
      if (data.success) {
        setHotlistData(data.platforms);
      } else {
        setError('获取热榜数据失败');
      }
    } catch (err) {
      console.error('加载热榜失败:', err);
      setError('网络错误，请重试');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedPlatforms]);

  // 平台选择变化时重新加载
  useEffect(() => {
    if (selectedPlatforms.length > 0) {
      loadHotlist();
    }
  }, [selectedPlatforms, loadHotlist]);

  // 刷新数据
  const handleRefresh = () => {
    setRefreshing(true);
    loadHotlist(true);
  };

  // 平台选择
  const togglePlatform = (platformId: string) => {
    setSelectedPlatforms(prev => {
      if (prev.includes(platformId)) {
        return prev.filter(id => id !== platformId);
      }
      return [...prev, platformId];
    });
  };

  // 全选/取消全选
  const toggleAll = () => {
    if (selectedPlatforms.length === platforms.length) {
      setSelectedPlatforms([]);
    } else {
      setSelectedPlatforms(platforms.map(p => p.id));
    }
  };

  // 关键词管理
  const addKeyword = () => {
    const kw = keywordInput.trim();
    if (kw && !keywords.includes(kw)) {
      setKeywords([...keywords, kw]);
      setKeywordInput('');
    }
  };

  const removeKeyword = (kw: string) => {
    setKeywords(keywords.filter(k => k !== kw));
  };

  // 筛选热点
  const filterItems = (items: HotItem[]): HotItem[] => {
    if (keywords.length === 0) return items;

    return items.filter(item => {
      const title = item.title.toLowerCase();
      return keywords.some(kw => {
        const k = kw.toLowerCase();
        if (k.startsWith('!')) {
          return !title.includes(k.slice(1));
        }
        return title.includes(k);
      });
    });
  };

  // AI 分析
  const handleAnalyze = async () => {
    setAnalyzing(true);
    setShowAnalysis(true);
    setAnalysisResult(null);

    try {
      const result = await trendradarApi.analyze({
        platform_ids: selectedPlatforms,
        keywords: keywords.length > 0 ? keywords : undefined,
        include_rss: false,
        max_news: 50,
      });
      setAnalysisResult(result);
    } catch (err) {
      console.error('AI 分析失败:', err);
      setAnalysisResult({
        success: false,
        error: 'AI 分析请求失败，请检查网络或稍后重试',
      });
    } finally {
      setAnalyzing(false);
    }
  };

  // 返回工具选择首页
  const handleBack = () => {
    navigate('/login');
  };

  // 计算统计
  const totalItems = Object.values(hotlistData).reduce(
    (sum, p) => sum + (p.success ? p.items.length : 0),
    0
  );

  const filteredTotal = Object.values(hotlistData).reduce(
    (sum, p) => sum + (p.success ? filterItems(p.items).length : 0),
    0
  );

  return (
    <div className="trendradar-page">
      {/* 顶部导航 */}
      <header className="trendradar-header">
        <button className="back-btn" onClick={handleBack}>
          &larr; 返回
        </button>
        <h1>热点监控</h1>
        <div className="header-spacer"></div>
      </header>

      {/* 平台选择 */}
      <section className="platform-section">
        <div className="section-header">
          <h2>选择平台</h2>
          <button className="toggle-all-btn" onClick={toggleAll}>
            {selectedPlatforms.length === platforms.length ? '取消全选' : '全选'}
          </button>
        </div>
        <div className="platform-grid">
          {platforms.map(platform => (
            <label
              key={platform.id}
              className={`platform-chip ${selectedPlatforms.includes(platform.id) ? 'selected' : ''}`}
            >
              <input
                type="checkbox"
                checked={selectedPlatforms.includes(platform.id)}
                onChange={() => togglePlatform(platform.id)}
              />
              <span>{platform.name}</span>
            </label>
          ))}
        </div>
      </section>

      {/* 关键词筛选 */}
      <section className="keyword-section">
        <div className="section-header">
          <h2>关键词筛选</h2>
          <span className="hint">输入关键词回车添加，!开头表示排除</span>
        </div>
        <div className="keyword-input-row">
          <input
            type="text"
            value={keywordInput}
            onChange={e => setKeywordInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addKeyword()}
            placeholder="输入关键词..."
          />
          <button onClick={addKeyword}>添加</button>
        </div>
        {keywords.length > 0 && (
          <div className="keyword-tags">
            {keywords.map(kw => (
              <span key={kw} className={`keyword-tag ${kw.startsWith('!') ? 'exclude' : ''}`}>
                {kw}
                <button onClick={() => removeKeyword(kw)}>&times;</button>
              </span>
            ))}
          </div>
        )}
      </section>

      {/* 操作栏 */}
      <section className="action-bar">
        <div className="stats">
          <span>已选 {selectedPlatforms.length} 个平台</span>
          <span>
            {keywords.length > 0
              ? `筛选后 ${filteredTotal} / ${totalItems} 条`
              : `共 ${totalItems} 条热点`}
          </span>
        </div>
        <div className="actions">
          <button
            className="refresh-btn"
            onClick={handleRefresh}
            disabled={loading || refreshing}
          >
            {refreshing ? '刷新中...' : '刷新数据'}
          </button>
          <button
            className="analyze-btn"
            onClick={handleAnalyze}
            disabled={analyzing || totalItems === 0}
          >
            {analyzing ? 'AI 分析中...' : 'AI 智能分析'}
          </button>
        </div>
      </section>

      {/* 错误提示 */}
      {error && <div className="error-message">{error}</div>}

      {/* AI 分析结果 */}
      {showAnalysis && (
        <section className="analysis-section">
          <div className="section-header">
            <h2>AI 分析报告</h2>
            <button className="close-btn" onClick={() => setShowAnalysis(false)}>
              &times;
            </button>
          </div>
          {analyzing ? (
            <div className="analysis-loading">
              <div className="spinner"></div>
              <p>AI 正在分析热点趋势，请稍候...</p>
            </div>
          ) : analysisResult ? (
            <div className="analysis-content">
              {analysisResult.success ? (
                <>
                  {analysisResult.from_cache && (
                    <div className="cache-hint">来自缓存</div>
                  )}
                  {analysisResult.summary && (
                    <div className="analysis-block">
                      <h3>热点趋势概述</h3>
                      {renderAnalysisContent(analysisResult.summary)}
                    </div>
                  )}
                  {analysisResult.keyword_analysis && (
                    <div className="analysis-block">
                      <h3>关键词分析</h3>
                      {renderKeywordTable(analysisResult.keyword_analysis)}
                    </div>
                  )}
                  {analysisResult.sentiment && (
                    <div className="analysis-block">
                      <h3>情感倾向</h3>
                      {renderAnalysisContent(analysisResult.sentiment)}
                    </div>
                  )}
                  {analysisResult.cross_platform && (
                    <div className="analysis-block">
                      <h3>跨平台关联</h3>
                      {renderAnalysisContent(analysisResult.cross_platform)}
                    </div>
                  )}
                  {analysisResult.signals && (
                    <div className="analysis-block">
                      <h3>值得关注</h3>
                      {renderAnalysisContent(analysisResult.signals)}
                    </div>
                  )}
                  {analysisResult.conclusion && (
                    <div className="analysis-block conclusion">
                      <h3>总结与建议</h3>
                      {renderAnalysisContent(analysisResult.conclusion)}
                    </div>
                  )}
                  {analysisResult.stats && (
                    <div className="analysis-stats">
                      分析了 {analysisResult.stats.analyzed_news} 条新闻
                      （热榜 {analysisResult.stats.hotlist_count} + RSS {analysisResult.stats.rss_count}）
                    </div>
                  )}
                </>
              ) : (
                <div className="analysis-error">
                  {analysisResult.error || '分析失败'}
                </div>
              )}
            </div>
          ) : null}
        </section>
      )}

      {/* 热榜列表 */}
      <section className="hotlist-section">
        {loading && !refreshing ? (
          <div className="loading">
            <div className="spinner"></div>
            <p>加载中...</p>
          </div>
        ) : (
          <div className="hotlist-grid">
            {selectedPlatforms.map(platformId => {
              const data = hotlistData[platformId];
              if (!data) return null;

              const items = filterItems(data.items);

              return (
                <div key={platformId} className="platform-card">
                  <div className="platform-card-header">
                    <h3>{data.platform_name}</h3>
                    <span className="item-count">
                      {keywords.length > 0 ? `${items.length}/${data.count}` : data.count}
                    </span>
                    {data.cached && <span className="cached-badge">缓存</span>}
                  </div>
                  {data.success ? (
                    <ul className="hotlist">
                      {items.slice(0, 20).map((item, idx) => (
                        <li key={idx} className={item.rank <= 3 ? 'top-rank' : ''}>
                          <span className="rank">{item.rank}</span>
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={item.title}
                          >
                            {item.title}
                          </a>
                        </li>
                      ))}
                      {items.length === 0 && (
                        <li className="no-match">无匹配结果</li>
                      )}
                    </ul>
                  ) : (
                    <div className="platform-error">{data.error || '加载失败'}</div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
};
