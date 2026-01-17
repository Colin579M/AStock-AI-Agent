/**
 * 历史报告回看页面
 *
 * 三栏式布局：左侧股票列表、中间日期列表、右侧报告预览
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { analysisApi } from '../../api/client';
import './HistoryPage.css';

interface Stock {
  ticker: string;
  latest_date: string;
  report_count: number;
}

interface DateItem {
  date: string;
  has_summary: boolean;
  reports: string[];
}

const REPORT_TYPES = [
  { key: 'final_report', name: '综合报告', icon: '📝' },
  { key: 'market_report', name: '市场分析', icon: '📊' },
  { key: 'sentiment_report', name: '情绪分析', icon: '💬' },
  { key: 'news_report', name: '新闻分析', icon: '📰' },
  { key: 'fundamentals_report', name: '基本面', icon: '📈' },
];

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();

  // 股票列表
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [stocksLoading, setStocksLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // 选中的股票及其日期列表
  const [selectedStock, setSelectedStock] = useState<string | null>(null);
  const [dates, setDates] = useState<DateItem[]>([]);
  const [datesLoading, setDatesLoading] = useState(false);

  // 选中的日期及报告
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedReportType, setSelectedReportType] = useState('final_report');
  const [reportContent, setReportContent] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  // 加载股票列表
  useEffect(() => {
    const loadStocks = async () => {
      try {
        const data = await analysisApi.browseAllStocks();
        setStocks(data.stocks);
      } catch (err) {
        console.error('加载股票列表失败:', err);
      } finally {
        setStocksLoading(false);
      }
    };
    loadStocks();
  }, []);

  // 加载日期列表
  useEffect(() => {
    if (!selectedStock) {
      setDates([]);
      return;
    }

    const loadDates = async () => {
      setDatesLoading(true);
      try {
        const data = await analysisApi.getStockReportDates(selectedStock);
        setDates(data.dates);
        // 自动选择最新日期
        if (data.dates.length > 0) {
          setSelectedDate(data.dates[0].date);
        }
      } catch (err) {
        console.error('加载日期列表失败:', err);
      } finally {
        setDatesLoading(false);
      }
    };
    loadDates();
  }, [selectedStock]);

  // 加载报告内容
  useEffect(() => {
    if (!selectedStock || !selectedDate) {
      setReportContent(null);
      return;
    }

    const loadReport = async () => {
      setReportLoading(true);
      try {
        const data = await analysisApi.getHistoricalReport(
          selectedStock,
          selectedDate,
          selectedReportType
        );
        setReportContent(data.content);
      } catch (err) {
        console.error('加载报告失败:', err);
        setReportContent(null);
      } finally {
        setReportLoading(false);
      }
    };
    loadReport();
  }, [selectedStock, selectedDate, selectedReportType]);

  // 搜索模式：只有输入搜索词时才显示匹配的股票
  const filteredStocks = searchQuery.trim()
    ? stocks.filter((s) =>
        s.ticker.toLowerCase().includes(searchQuery.toLowerCase().trim())
      )
    : [];

  // 判断搜索状态
  const hasSearchQuery = searchQuery.trim().length > 0;
  const hasResults = filteredStocks.length > 0;

  return (
    <div className="history-page">
      {/* 顶部导航栏 */}
      <header className="history-header">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← 返回首页
        </button>
        <h1>历史报告</h1>
        <div className="header-spacer" />
      </header>

      {/* 三栏布局 */}
      <div className="history-content">
        {/* 左栏：搜索框 + 结果 */}
        <div className="stock-list-panel compact">
          <div className="search-box">
            <input
              type="text"
              placeholder="输入股票代码..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          {hasSearchQuery && (
            <div className="stock-list">
              {stocksLoading ? (
                <div className="loading">加载中...</div>
              ) : !hasResults ? (
                <div className="no-result">
                  <span>暂无记录，请先分析</span>
                </div>
              ) : (
                filteredStocks.map((stock) => (
                  <div
                    key={stock.ticker}
                    className={`stock-item ${selectedStock === stock.ticker ? 'active' : ''}`}
                    onClick={() => setSelectedStock(stock.ticker)}
                  >
                    <div className="stock-ticker">{stock.ticker}</div>
                    <div className="stock-meta">
                      <span className="latest-date">{stock.latest_date}</span>
                      <span className="report-count">{stock.report_count} 次</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* 中栏：日期列表 */}
        <div className="date-list-panel">
          <div className="panel-header">
            <h2>{selectedStock ? `${selectedStock} 分析记录` : '选择股票'}</h2>
            {dates.length > 0 && <span className="count">{dates.length} 条</span>}
          </div>
          <div className="date-list">
            {!selectedStock ? (
              <div className="empty">← 请先选择股票</div>
            ) : datesLoading ? (
              <div className="loading">加载中...</div>
            ) : dates.length === 0 ? (
              <div className="empty">暂无分析记录</div>
            ) : (
              dates.map((item) => (
                <div
                  key={item.date}
                  className={`date-item ${selectedDate === item.date ? 'active' : ''}`}
                  onClick={() => setSelectedDate(item.date)}
                >
                  <div className="date-value">{item.date}</div>
                  <div className="date-reports">
                    {item.reports.includes('final_report') && (
                      <span className="report-badge final">综合</span>
                    )}
                    {item.reports.filter((r) => r !== 'final_report').length > 0 && (
                      <span className="report-badge">
                        +{item.reports.filter((r) => r !== 'final_report').length} 份报告
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 右栏：报告预览 */}
        <div className="report-preview-panel">
          <div className="panel-header">
            <h2>报告预览</h2>
            {selectedStock && selectedDate && (
              <div className="report-tabs">
                {REPORT_TYPES.map((rt) => (
                  <button
                    key={rt.key}
                    className={`tab-btn ${selectedReportType === rt.key ? 'active' : ''}`}
                    onClick={() => setSelectedReportType(rt.key)}
                    title={rt.name}
                  >
                    {rt.icon}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="report-content">
            {!selectedStock || !selectedDate ? (
              <div className="empty-state">
                <div className="empty-icon">📄</div>
                <p>选择股票和日期查看报告</p>
              </div>
            ) : reportLoading ? (
              <div className="loading-state">
                <div className="spinner" />
                <p>加载报告中...</p>
              </div>
            ) : !reportContent ? (
              <div className="empty-state">
                <div className="empty-icon">📭</div>
                <p>该报告不存在</p>
              </div>
            ) : (
              <div className="markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {reportContent}
                </ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
