/**
 * 分析维度选择器组件
 *
 * 让用户选择深度分析的维度，支持单选和全选。
 * 受 Google Gemini 股票研究提示启发设计。
 */
import React from 'react';
import './AnalysisSelector.css';

// 分析维度定义
export interface AnalysisDimension {
  id: string;
  name: string;
  icon: string;
  description: string;
}

// 8 个核心分析维度
export const ANALYSIS_DIMENSIONS: AnalysisDimension[] = [
  { id: 'business', name: '业务理解', icon: '🏢', description: '公司做什么，护城河在哪' },
  { id: 'revenue', name: '收入分解', icon: '📊', description: '哪块业务在增长/放缓' },
  { id: 'industry', name: '行业背景', icon: '🌐', description: '市场趋势对公司的影响' },
  { id: 'competition', name: '竞争格局', icon: '⚔️', description: '与对手的优劣势对比' },
  { id: 'financials', name: '财务质量', icon: '💰', description: '收入、利润、现金流' },
  { id: 'risks', name: '风险分析', icon: '⚠️', description: '最大的风险是什么' },
  { id: 'valuation', name: '估值思考', icon: '🎯', description: '当前估值是否合理' },
  { id: 'thesis', name: '投资论点', icon: '📝', description: '牛熊情景 + 长期观点' },
];

// 快捷分析选项
export const QUICK_ANALYSIS_OPTIONS = [
  { command: '/快速估值', name: '快速估值', icon: '🎯' },
  { command: '/风险扫描', name: '风险扫描', icon: '⚠️' },
  { command: '/财务体检', name: '财务体检', icon: '💰' },
  { command: '/投资论点', name: '投资论点', icon: '📝' },
];

interface AnalysisSelectorProps {
  stockName: string;
  onSelect: (dimensions: string[]) => void;
  onQuickCommand: (command: string) => void;
  onClose?: () => void;
}

export const AnalysisSelector: React.FC<AnalysisSelectorProps> = ({
  stockName,
  onSelect,
  onQuickCommand,
  onClose,
}) => {
  const [selectedDimensions, setSelectedDimensions] = React.useState<string[]>([]);

  const toggleDimension = (id: string) => {
    setSelectedDimensions(prev =>
      prev.includes(id)
        ? prev.filter(d => d !== id)
        : [...prev, id]
    );
  };

  const selectAll = () => {
    setSelectedDimensions(ANALYSIS_DIMENSIONS.map(d => d.id));
  };

  const clearAll = () => {
    setSelectedDimensions([]);
  };

  const handleAnalyze = () => {
    if (selectedDimensions.length > 0) {
      onSelect(selectedDimensions);
    }
  };

  const handleFullAnalysis = () => {
    onSelect(ANALYSIS_DIMENSIONS.map(d => d.id));
  };

  return (
    <div className="analysis-selector">
      <div className="analysis-selector-header">
        <h3>📋 {stockName} 深度分析</h3>
        {onClose && (
          <button className="close-btn" onClick={onClose}>×</button>
        )}
      </div>

      {/* 快捷选项 */}
      <div className="quick-options">
        <p className="section-label">快捷分析：</p>
        <div className="quick-options-grid">
          {QUICK_ANALYSIS_OPTIONS.map(opt => (
            <button
              key={opt.command}
              className="quick-option-btn"
              onClick={() => onQuickCommand(`${opt.command} ${stockName}`)}
            >
              {opt.icon} {opt.name}
            </button>
          ))}
        </div>
      </div>

      {/* 维度选择 */}
      <div className="dimension-selection">
        <div className="section-header">
          <p className="section-label">选择分析维度：</p>
          <div className="selection-actions">
            <button className="text-btn" onClick={selectAll}>全选</button>
            <button className="text-btn" onClick={clearAll}>清空</button>
          </div>
        </div>

        <div className="dimensions-grid">
          {ANALYSIS_DIMENSIONS.map(dim => (
            <button
              key={dim.id}
              className={`dimension-btn ${selectedDimensions.includes(dim.id) ? 'selected' : ''}`}
              onClick={() => toggleDimension(dim.id)}
            >
              <span className="dimension-icon">{dim.icon}</span>
              <span className="dimension-name">{dim.name}</span>
              <span className="dimension-desc">{dim.description}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="action-buttons">
        <button
          className="analyze-btn secondary"
          onClick={handleFullAnalysis}
        >
          🔄 全面分析（8个维度）
        </button>
        <button
          className="analyze-btn primary"
          onClick={handleAnalyze}
          disabled={selectedDimensions.length === 0}
        >
          开始分析 ({selectedDimensions.length} 个维度)
        </button>
      </div>

      {/* 提示 */}
      <div className="tip">
        💡 也可以直接输入快捷命令，如：<code>/深度分析 {stockName}</code>
      </div>
    </div>
  );
};

export default AnalysisSelector;
