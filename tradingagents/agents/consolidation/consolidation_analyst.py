"""
A股综合研报生成器

整合7份分析报告，生成专业、结构清晰、可执行的综合投资研究报告
"""

from typing import Any, Dict


CONSOLIDATION_SYSTEM_PROMPT = '''您是一位资深的A股投资研究总监，负责整合团队的研究成果并撰写最终的综合研究报告。

## 输入报告

您将收到以下7份独立分析报告：
1. **市场技术分析报告** - 技术指标、趋势分析、支撑/阻力位
2. **市场情绪报告** - 资金流向、千股千评、北向资金
3. **新闻舆情报告** - 公司新闻、行业动态、宏观政策
4. **基本面分析报告** - 财报分析、估值指标、盈利能力
5. **投资计划** - 研究团队的多空辩论结论
6. **交易员计划** - 具体的交易策略建议
7. **最终交易决策** - 风险评估团队的综合判断

## 报告要求

请生成一份**专业、结构清晰、可执行**的综合投资研究报告，包含以下部分：

### 1. 执行摘要 (Executive Summary)
- 投资评级：【强烈买入/买入/持有/减持/卖出】
- 目标价位：基于估值分析给出合理目标价
- 核心投资逻辑（3-5点，每点一句话概括）
- 主要风险提示（2-3点）

### 2. 多维度分析汇总

#### 2.1 基本面评估
- 盈利能力与成长性（引用具体财务数据）
- 估值水平合理性（PE/PB与行业对比）
- 财务健康度（资产负债率、现金流等）

#### 2.2 技术面评估
- 当前趋势判断（多头/空头/震荡）
- 关键价位（支撑位/阻力位，给出具体数字）
- 技术指标信号（RSI、MACD等信号解读）

#### 2.3 资金面评估
- 主力资金动向（净流入/流出金额）
- 北向资金态度（增持/减持）
- 市场情绪指标（热度排名、千股千评等）

#### 2.4 消息面评估
- 重大利好/利空（具体事件）
- 行业政策影响
- 宏观经济背景（PMI等指标）

### 3. 投资建议

#### 3.1 操作策略
- **建议仓位**：给出具体百分比
- **入场时机**：描述具体触发条件
- **目标价位**：短期（1个月）/ 中期（3-6个月）目标
- **止损价位**：风险控制点位

#### 3.2 分批建仓计划（如适用）
| 批次 | 价位区间 | 仓位占比 | 触发条件 |
|------|---------|---------|---------|
| 第一批 | | | |
| 第二批 | | | |

### 4. 风险评估矩阵

| 风险类型 | 风险描述 | 概率 | 影响程度 | 应对措施 |
|---------|---------|------|---------|---------|
| 市场风险 | 大盘系统性下跌 | 低/中/高 | 低/中/高 | 设置止损 |
| 行业风险 | 商品价格波动 | 低/中/高 | 低/中/高 | 分散配置 |
| 公司风险 | 业绩不及预期 | 低/中/高 | 低/中/高 | 跟踪季报 |

### 5. 关键监测指标

列出投资者应持续关注的关键指标和事件：
- 下一财报发布日期（如有）
- 重要股东会议/增减持公告
- 行业政策变化节点
- 技术突破/跌破关键点位

### 6. 免责声明

本报告由AI系统自动生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。

---

## 格式要求
- 使用 Markdown 格式
- 数据引用需标明来源报告（如：据基本面分析，PE为18.64）
- 观点需有数据支撑，避免空泛表述
- 语言专业但易于理解
- 建议必须具体、可操作，避免模糊表述

## 重要原则
1. **客观中立**：综合多方观点，不偏向单一分析师意见
2. **逻辑自洽**：最终结论必须与各维度分析相符，不能自相矛盾
3. **风险优先**：充分揭示风险，宁可保守也不过度乐观
4. **可执行性**：建议必须具体到价位、仓位、时机
5. **专业严谨**：数据准确引用，表述规范专业
'''


def create_consolidation_analyst(llm):
    """
    创建A股综合研报分析师节点

    Args:
        llm: 语言模型实例

    Returns:
        consolidation_node: 综合报告生成节点函数
    """

    def consolidation_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        整合所有分析报告，生成综合研报

        Args:
            state: 包含所有分析报告的状态字典

        Returns:
            包含 consolidation_report 的字典
        """
        ticker = state.get("company_of_interest", "未知股票")
        trade_date = state.get("trade_date", "未知日期")

        # 获取股票名称（如果有的话）
        stock_name = ""
        market_report = state.get("market_report", "")
        if "名称" in market_report:
            # 尝试从市场报告中提取股票名称
            import re
            name_match = re.search(r'名称[：:]\s*(\S+)', market_report)
            if name_match:
                stock_name = name_match.group(1)

        # 构建输入材料
        input_materials = f"""
# {stock_name}（{ticker}）综合分析材料

**分析日期**: {trade_date}
**生成时间**: 由 TradingAgents AI Research 系统生成

---

## 报告 1：市场技术分析

{state.get("market_report", "暂无数据")}

---

## 报告 2：市场情绪分析

{state.get("sentiment_report", "暂无数据")}

---

## 报告 3：新闻舆情分析

{state.get("news_report", "暂无数据")}

---

## 报告 4：基本面分析

{state.get("fundamentals_report", "暂无数据")}

---

## 报告 5：投资计划（研究团队多空辩论结论）

{state.get("investment_plan", "暂无数据")}

---

## 报告 6：交易员执行计划

{state.get("trader_investment_plan", "暂无数据")}

---

## 报告 7：最终交易决策（风险评估团队）

{state.get("final_trade_decision", "暂无数据")}

---

请根据以上7份报告，生成一份专业的综合投资研究报告。
"""

        # 构建消息
        messages = [
            {"role": "system", "content": CONSOLIDATION_SYSTEM_PROMPT},
            {"role": "user", "content": input_materials}
        ]

        # 调用LLM生成报告
        try:
            response = llm.invoke(messages)
            consolidation_report = response.content
        except Exception as e:
            consolidation_report = f"""
# {stock_name}（{ticker}）综合投资研究报告

**分析日期**: {trade_date}

---

## 报告生成失败

综合报告生成过程中发生错误: {str(e)}

请查看各独立分析报告获取详细信息。
"""

        return {
            "consolidation_report": consolidation_report
        }

    return consolidation_node


def is_china_stock(ticker: str) -> bool:
    """
    判断是否为中国A股股票代码

    Args:
        ticker: 股票代码

    Returns:
        bool: True 如果是中国A股代码
    """
    if not ticker:
        return False
    # 移除可能的后缀（如 .SS, .SZ）
    clean_ticker = ticker.split('.')[0]
    # 判断是否为6位数字
    if clean_ticker.isdigit() and len(clean_ticker) == 6:
        # 深圳：000xxx, 002xxx, 003xxx, 300xxx
        # 上海：600xxx, 601xxx, 603xxx, 605xxx, 688xxx
        prefix = clean_ticker[:3]
        if prefix in ['000', '002', '003', '300', '600', '601', '603', '605', '688']:
            return True
    return False
