/**
 * 全面分析页面
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { analysisApi } from '../../api/client';
import type { TaskStatus, AnalysisResult } from '../../api/client';
import './AnalysisPage.css';

// 分析步骤按团队分组（仿照 CLI UI）
const TEAMS = [
  {
    name: '分析师团队',
    icon: '📊',
    steps: [
      { key: 'market_analyst', name: '市场分析师' },
      { key: 'social_analyst', name: '情绪分析师' },
      { key: 'news_analyst', name: '新闻分析师' },
      { key: 'fundamentals_analyst', name: '基本面分析师' },
    ],
  },
  {
    name: '研究团队',
    icon: '🔬',
    steps: [
      { key: 'bull_researcher', name: '看涨研究员' },
      { key: 'bear_researcher', name: '看跌研究员' },
      { key: 'research_manager', name: '研究主管' },
    ],
  },
  {
    name: '风控团队',
    icon: '🛡️',
    steps: [
      { key: 'risky_manager', name: '激进风控' },
      { key: 'conservative_manager', name: '保守风控' },
      { key: 'neutral_manager', name: '中立风控' },
      { key: 'risk_manager', name: '风险主管' },
    ],
  },
  {
    name: '综合报告',
    icon: '📝',
    steps: [{ key: 'consolidation', name: '生成报告' }],
  },
];

// 获取所有步骤的 key 列表
const ALL_STEPS = TEAMS.flatMap((team) => team.steps.map((s) => s.key));

// 分析师步骤到报告类型的映射
const ANALYST_REPORT_MAP: Record<string, string> = {
  'market_analyst': 'market_report',
  'social_analyst': 'sentiment_report',
  'news_analyst': 'news_report',
  'fundamentals_analyst': 'fundamentals_report',
};

export const AnalysisPage: React.FC = () => {
  const navigate = useNavigate();
  const { taskId: urlTaskId } = useParams();

  const [ticker, setTicker] = useState('');
  const [tickerName, setTickerName] = useState('');
  const [taskId, setTaskId] = useState<string | undefined>(urlTaskId);
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState('');
  const [expandedReport, setExpandedReport] = useState<string | null>(null);

  // 预览报告相关状态
  const [previewReport, setPreviewReport] = useState<{
    type: string;
    name: string;
    content: string;
  } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const logsContainerRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 自动滚动日志容器（只滚动容器内部，不影响页面）
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [status?.logs]);

  // 轮询任务状态
  useEffect(() => {
    if (!taskId) return;

    const pollStatus = async () => {
      try {
        const taskStatus = await analysisApi.getTaskStatus(taskId);
        setStatus(taskStatus);

        if (taskStatus.status === 'completed') {
          // 获取结果
          const taskResult = await analysisApi.getTaskResult(taskId);
          setResult(taskResult);
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
        } else if (taskStatus.status === 'failed') {
          setError(taskStatus.error || '分析失败');
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
        }
      } catch (err) {
        console.error('获取状态失败:', err);
      }
    };

    pollStatus();
    pollIntervalRef.current = setInterval(pollStatus, 2000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [taskId]);

  const handleStartAnalysis = async () => {
    if (!ticker.trim()) {
      setError('请输入股票代码');
      return;
    }

    setError('');
    setResult(null);

    try {
      const response = await analysisApi.startAnalysis(ticker, tickerName);
      if (response.success) {
        setTaskId(response.task_id);
        navigate(`/analysis/${response.task_id}`, { replace: true });
      } else {
        setError('启动分析失败');
      }
    } catch (err: any) {
      // 显示后端返回的具体错误信息
      const errorMessage = err?.response?.data?.detail || err?.message || '网络错误，请重试';
      setError(errorMessage);
    }
  };

  const handleCancelAnalysis = async () => {
    // 停止轮询
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    // 调用后端取消 API
    if (taskId) {
      try {
        await analysisApi.cancelTask(taskId);
      } catch (err) {
        // 忽略取消失败（可能任务已完成）
        console.log('取消任务:', err);
      }
    }
    // 重置状态
    setTaskId(undefined);
    setStatus(null);
    setResult(null);
    setError('');
    setTicker('');
    setTickerName('');
    // 返回主页
    navigate('/home');
  };

  const getStepStatus = (step: string): 'done' | 'current' | 'pending' => {
    if (!status) return 'pending';
    if (status.progress.completed_steps.includes(step)) return 'done';
    if (status.progress.current_step === step) return 'current';
    // 支持并行分析师状态
    const activeAnalysts = status.progress.active_analysts || [];
    const activeAnalyst = activeAnalysts.find((a: { key: string; status: string }) => a.key === step);
    if (activeAnalyst && activeAnalyst.status === 'running') return 'current';
    return 'pending';
  };

  // 预览分析师报告
  const handlePreviewReport = async (stepKey: string) => {
    const reportType = ANALYST_REPORT_MAP[stepKey];
    if (!reportType) return;

    setPreviewLoading(true);
    try {
      // 如果有 result（分析已完成），使用历史报告 API
      if (result) {
        const ticker = result.ticker.split('.')[0];
        const date = status?.date || new Date().toISOString().split('T')[0];
        const data = await analysisApi.getHistoricalReport(ticker, date, reportType);
        setPreviewReport({
          type: reportType,
          name: data.report_name,
          content: data.content,
        });
      } else if (taskId) {
        // 分析进行中，使用中间报告 API
        const data = await analysisApi.getIntermediateReport(taskId, reportType);
        setPreviewReport({
          type: reportType,
          name: data.report_name,
          content: data.content,
        });
      }
    } catch (err) {
      console.error('获取报告失败:', err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const getDecisionStyle = (decision?: string) => {
    if (!decision) return {};
    const d = decision.toLowerCase();
    if (d.includes('买') || d.includes('buy'))
      return { background: '#dcfce7', color: '#15803d' };
    if (d.includes('卖') || d.includes('sell'))
      return { background: '#fee2e2', color: '#dc2626' };
    return { background: '#fef3c7', color: '#d97706' };
  };

  // 显示结果视图
  if (result) {
    return (
      <div className="analysis-page">
        <header className="analysis-header">
          <button className="back-btn" onClick={() => navigate('/home')}>
            ←
          </button>
          <h1>分析报告</h1>
          <div />
        </header>

        <div className="result-container">
          <div className="result-header">
            <h2>
              {status?.ticker_name || result.ticker}
              <span className="ticker-code">
                ({result.ticker.split('.')[0]})
              </span>
            </h2>
            <p className="result-date">生成时间: {status?.date}</p>
          </div>

          {/* 决策摘要 */}
          <div className="decision-card" style={getDecisionStyle(result.decision)}>
            <div className="decision-main">
              <span className="decision-label">投资建议</span>
              <span className="decision-value">{result.decision}</span>
            </div>
            {result.summary?.target_price && (
              <div className="decision-detail">
                <span>目标价</span>
                <span>¥{result.summary.target_price.toFixed(2)}</span>
              </div>
            )}
            {result.summary?.confidence && (
              <div className="decision-detail">
                <span>置信度</span>
                <span>{(result.summary.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>

          {/* 综合报告 */}
          {result.reports.consolidation_report && (
            <div className="report-section main-report">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {result.reports.consolidation_report.content}
              </ReactMarkdown>
            </div>
          )}

          {/* 详细报告折叠 */}
          <div className="detailed-reports">
            <h3>详细分析报告</h3>
            {Object.entries(result.reports)
              .filter(([key]) => key !== 'consolidation_report')
              .map(([key, report]) => (
                <div key={key} className="report-item">
                  <button
                    className={`report-toggle ${
                      expandedReport === key ? 'expanded' : ''
                    }`}
                    onClick={() =>
                      setExpandedReport(expandedReport === key ? null : key)
                    }
                  >
                    <span>{report.name}</span>
                    <span className="toggle-icon">
                      {expandedReport === key ? '▼' : '▶'}
                    </span>
                  </button>
                  {expandedReport === key && (
                    <div className="report-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
              ))}
          </div>

          <div className="result-actions">
            <button
              className="action-btn"
              onClick={() => {
                setTaskId(undefined);
                setResult(null);
                setStatus(null);
                navigate('/analysis');
              }}
            >
              再次分析
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 显示进行中或输入视图
  return (
    <div className="analysis-page">
      <header className="analysis-header">
        <button className="back-btn" onClick={() => navigate('/home')}>
          ←
        </button>
        <h1>全面分析报告</h1>
        <div />
      </header>

      {/* 输入表单 */}
      {!taskId && (
        <>
          <div className="input-section">
            <p className="input-hint">输入股票代码或名称</p>
            <div className="input-row">
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="如 600036"
                className="ticker-input"
              />
              <input
                type="text"
                value={tickerName}
                onChange={(e) => setTickerName(e.target.value)}
                placeholder="招商银行（可选）"
                className="name-input"
              />
            </div>
            {error && <div className="error-message">{error}</div>}
            <button className="start-btn" onClick={handleStartAnalysis}>
              开始分析
            </button>
          </div>

          {/* 系统介绍 - 信息图表风格 */}
          <div className="infographic-intro">
            <div className="intro-header">
              <h2>AI 投研团队协作分析</h2>
              <p>模拟专业机构的多团队研究流程，输出综合投资建议</p>
            </div>

            {/* 上方分析节点 */}
            <div className="analysis-nodes top-row">
              <div className="analysis-node">
                <span className="node-icon">📊</span>
                <span className="node-label">行情数据</span>
              </div>
              <div className="analysis-node">
                <span className="node-icon">📰</span>
                <span className="node-label">新闻分析</span>
              </div>
              <div className="analysis-node">
                <span className="node-icon">💬</span>
                <span className="node-label">舆情监测</span>
              </div>
            </div>

            {/* 中心决策圆环 */}
            <div className="center-decision">
              <span className="decision-icon">🎯</span>
              <span className="decision-label">投资决策</span>
              <span className="decision-output">BUY / SELL / HOLD</span>
            </div>

            {/* 下方分析节点 */}
            <div className="analysis-nodes bottom-row">
              <div className="analysis-node">
                <span className="node-icon">📈</span>
                <span className="node-label">基本面</span>
              </div>
              <div className="analysis-node debate">
                <span className="node-icon">🐂🐻</span>
                <span className="node-label">多空辩论</span>
              </div>
              <div className="analysis-node">
                <span className="node-icon">⚖️</span>
                <span className="node-label">风险评估</span>
              </div>
            </div>

            {/* A股特色横条 */}
            <div className="china-features">
              <span className="china-label">🇨🇳 A股适配</span>
              <span className="china-tag">龙虎榜</span>
              <span className="china-tag">北向资金</span>
              <span className="china-tag">涨跌停</span>
              <span className="china-tag">ST预警</span>
            </div>
          </div>
        </>
      )}

      {/* 进度面板 */}
      {status && status.status !== 'completed' && (
        <div className="progress-section">
          {/* 当前状态卡片 */}
          {(status.progress.current_step || (status.progress.active_analysts && status.progress.active_analysts.length > 0)) && (
            <div className="current-step-card">
              <div className="current-step-indicator">
                <span className="spinner large" />
                <div className="current-step-info">
                  <span className="current-step-label">正在执行</span>
                  <span className="current-step-name">
                    {/* 并行分析师模式 */}
                    {status.progress.active_analysts && status.progress.active_analysts.length > 0 ? (
                      (() => {
                        const running = status.progress.active_analysts.filter((a: { status: string }) => a.status === 'running');
                        const completed = status.progress.active_analysts.filter((a: { status: string }) => a.status === 'completed');
                        if (running.length > 0) {
                          return `${running.length}个分析师并行分析中`;
                        } else if (completed.length === status.progress.active_analysts.length) {
                          return '分析师团队已完成';
                        }
                        return status.progress.current_step_name || status.progress.current_step;
                      })()
                    ) : (
                      status.progress.current_step_name || status.progress.current_step
                    )}
                  </span>
                  <span className="current-step-hint">
                    AI 分析中，请耐心等待...
                  </span>
                </div>
              </div>
              <div className="current-step-ticker">
                {ticker || status.ticker_name}
              </div>
            </div>
          )}

          {/* 进度条 */}
          <div className="progress-bar-container">
            <div className="progress-bar-header">
              <span>分析进度</span>
              <span className="progress-percent">
                {Math.round(
                  (status.progress.completed_steps.length / ALL_STEPS.length) *
                    100
                )}
                %
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${
                    (status.progress.completed_steps.length / ALL_STEPS.length) *
                    100
                  }%`,
                }}
              />
            </div>
          </div>

          {/* 团队分组进度 */}
          <div className="teams-progress">
            {TEAMS.map((team) => {
              const teamCompleted = team.steps.filter((s) =>
                status.progress.completed_steps.includes(s.key)
              ).length;
              const teamTotal = team.steps.length;
              const teamStatus =
                teamCompleted === teamTotal
                  ? 'done'
                  : teamCompleted > 0 ||
                    team.steps.some(
                      (s) => status.progress.current_step === s.key
                    )
                  ? 'active'
                  : 'pending';

              return (
                <div key={team.name} className={`team-card ${teamStatus}`}>
                  <div className="team-header">
                    <span className="team-icon">{team.icon}</span>
                    <span className="team-name">{team.name}</span>
                    <span className="team-count">
                      {teamCompleted}/{teamTotal}
                    </span>
                  </div>
                  <div className="team-steps">
                    {team.steps.map((step) => {
                      const stepStatus = getStepStatus(step.key);
                      const hasReport = ANALYST_REPORT_MAP[step.key];
                      return (
                        <div
                          key={step.key}
                          className={`step-item ${stepStatus}`}
                        >
                          <span className="step-icon">
                            {stepStatus === 'done' && '✓'}
                            {stepStatus === 'current' && (
                              <span
                                style={{
                                  display: 'inline-block',
                                  width: 14,
                                  height: 14,
                                  border: '2px solid #9ca3af',
                                  borderTopColor: '#3b82f6',
                                  borderRadius: '50%',
                                  animation: 'spin 0.8s linear infinite',
                                }}
                              />
                            )}
                            {stepStatus === 'pending' && '○'}
                          </span>
                          <span className="step-name">{step.name}</span>
                          {stepStatus === 'current' && (
                            <span className="step-status">分析中...</span>
                          )}
                          {stepStatus === 'done' && hasReport && (
                            <button
                              className="preview-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePreviewReport(step.key);
                              }}
                              disabled={previewLoading}
                            >
                              预览
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {status.status === 'failed' && (
            <div className="error-message">{status.error}</div>
          )}

          {/* 实时日志 */}
          <div className="logs-section">
            <div className="logs-header">
              <h4>实时日志</h4>
              <span className="logs-count">{status.logs.length} 条记录</span>
            </div>
            <div className="logs-container" ref={logsContainerRef}>
              {status.logs.map((log, idx) => {
                // 根据日志内容添加不同样式
                const logClass =
                  log.includes('Tool') || log.includes('获取')
                    ? 'tool'
                    : log.includes('失败') || log.includes('错误')
                    ? 'error'
                    : log.includes('完成') || log.includes('✓')
                    ? 'success'
                    : '';
                return (
                  <div key={idx} className={`log-line ${logClass}`}>
                    {log}
                  </div>
                );
              })}
            </div>
          </div>

          {/* 取消按钮 */}
          <button className="cancel-btn" onClick={handleCancelAnalysis}>
            取消分析
          </button>
        </div>
      )}

      {/* 报告预览 Modal */}
      {previewReport && (
        <div className="preview-modal-overlay" onClick={() => setPreviewReport(null)}>
          <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="preview-modal-header">
              <h3>{previewReport.name}</h3>
              <button
                className="preview-modal-close"
                onClick={() => setPreviewReport(null)}
              >
                ✕
              </button>
            </div>
            <div className="preview-modal-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {previewReport.content}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
