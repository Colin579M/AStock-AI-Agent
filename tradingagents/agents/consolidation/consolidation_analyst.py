"""
A股综合研报生成器

整合7份分析报告，生成专业、结构清晰、可执行的综合投资研究报告
支持自动记录决策到 Memory，并在下次分析时查询历史决策
"""

import re
import logging
from typing import Any, Dict, Optional
from tradingagents.agents.utils.agent_utils import is_china_stock

logger = logging.getLogger(__name__)


CONSOLIDATION_SYSTEM_PROMPT = '''您是一位资深的A股投资研究总监，负责整合团队的研究成果并撰写最终的综合研究报告。

## 输入报告

您将收到以下8份分析材料：
1. **市场技术分析报告** - 技术指标、趋势分析、支撑/阻力位
2. **市场情绪报告** - 资金流向、千股千评、北向资金
3. **新闻舆情报告** - 公司新闻、行业动态、宏观政策
4. **基本面分析报告** - 财报分析、估值指标、盈利能力
5. **投资计划** - 研究团队的多空辩论结论
6. **交易员计划** - 具体的交易策略建议
7. **最终交易决策** - 风险评估团队的综合判断
8. **上次决策反思**（如有）- 上次分析的决策回顾、实际表现、经验教训

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

### 6. 历史决策回顾（仅当有上次决策反思时）

**重要**：仅当"报告8：上次决策反思"包含有效内容时才生成此部分。如果显示"首次分析此股票"或"无历史决策记录"，则**完全跳过此部分**，不要输出任何内容。

如果有有效的历史决策反思，请在此部分：
- 简要回顾上次决策及其结果（决策类型、当时价格、实际涨跌）
- 分析决策正确/错误的原因
- 说明本次分析如何吸收经验教训（例如：上次过于保守，本次需更关注XXX）

### 7. 免责声明

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


def _extract_decision_info(final_decision: str, consolidation_report: str) -> Dict[str, Any]:
    """
    从最终决策和综合报告中提取关键信息

    Returns:
        Dict: 包含 decision_type, confidence, target_price, stop_loss 等
    """
    info = {
        "decision_type": "HOLD",
        "confidence": 0.5,
        "target_price": None,
        "stop_loss": None,
        "position_size": None,
    }

    # 提取决策类型（中文和英文分开处理）
    decision_text = final_decision + " " + consolidation_report
    decision_text_upper = decision_text.upper()

    # 检查中文决策词（优先级从高到低）
    if "强烈买入" in decision_text:
        info["decision_type"] = "STRONG_BUY"
        info["confidence"] = 0.9
    elif "强烈卖出" in decision_text:
        info["decision_type"] = "STRONG_SELL"
        info["confidence"] = 0.9
    elif "买入" in decision_text and "强烈" not in decision_text:
        info["decision_type"] = "BUY"
        info["confidence"] = 0.7
    elif "卖出" in decision_text and "强烈" not in decision_text:
        info["decision_type"] = "SELL"
        info["confidence"] = 0.7
    elif "减持" in decision_text:
        info["decision_type"] = "REDUCE"
        info["confidence"] = 0.6
    elif "持有" in decision_text:
        info["decision_type"] = "HOLD"
        info["confidence"] = 0.5
    # 英文决策词
    elif "STRONG BUY" in decision_text_upper:
        info["decision_type"] = "STRONG_BUY"
        info["confidence"] = 0.9
    elif "BUY" in decision_text_upper:
        info["decision_type"] = "BUY"
        info["confidence"] = 0.7
    elif "SELL" in decision_text_upper:
        info["decision_type"] = "SELL"
        info["confidence"] = 0.7
    elif "HOLD" in decision_text_upper:
        info["decision_type"] = "HOLD"
        info["confidence"] = 0.5

    # 尝试提取目标价
    target_match = re.search(r'目标价[位]?[：:]\s*(\d+\.?\d*)', consolidation_report)
    if target_match:
        info["target_price"] = float(target_match.group(1))

    # 尝试提取止损价
    stop_match = re.search(r'止损价[位]?[：:]\s*(\d+\.?\d*)', consolidation_report)
    if stop_match:
        info["stop_loss"] = float(stop_match.group(1))

    # 尝试提取仓位
    position_match = re.search(r'建议仓位[：:]\s*(\d+)%', consolidation_report)
    if position_match:
        info["position_size"] = int(position_match.group(1))

    return info


def _format_historical_decisions(memories: list) -> str:
    """
    格式化历史决策为可读文本

    Args:
        memories: 从 memory.get_memories() 返回的记忆列表

    Returns:
        str: 格式化的历史决策文本
    """
    if not memories:
        return "首次分析此股票，无历史决策记录"

    result = []
    for i, mem in enumerate(memories, 1):
        similarity = mem.get("similarity_score", 0) * 100
        situation = mem.get("matched_situation", "")[:500]  # 截断过长内容
        recommendation = mem.get("recommendation", "")[:300]

        # 提取额外信息（如果有）
        decision_type = mem.get("decision_type", "未知")
        decision_date = mem.get("decision_date", "未知日期")
        actual_return = mem.get("actual_return")

        result.append(f"### 历史决策 {i} (相似度: {similarity:.1f}%)")
        result.append(f"**决策日期**: {decision_date}")
        result.append(f"**决策类型**: {decision_type}")

        if actual_return is not None:
            outcome = "盈利" if actual_return > 0 else "亏损"
            result.append(f"**实际结果**: {outcome} {abs(actual_return):.2f}%")

        result.append(f"\n**当时市场情况**:\n{situation}...")
        result.append(f"\n**当时建议**:\n{recommendation}...")
        result.append("\n---\n")

    return "\n".join(result)


def create_consolidation_analyst(llm, decision_memory=None):
    """
    创建A股综合研报分析师节点

    Args:
        llm: 语言模型实例
        decision_memory: 决策记忆存储（FinancialSituationMemory 实例）

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
            name_match = re.search(r'名称[：:]\s*(\S+)', market_report)
            if name_match:
                stock_name = name_match.group(1)

        # ========== 1. 查询历史决策 ==========
        previous_decision_reflection = "首次分析此股票，无历史决策记录"

        if decision_memory is not None:
            try:
                # 构建当前市场情况摘要（用于相似度匹配）
                current_situation = f"""
股票: {ticker} {stock_name}
日期: {trade_date}

市场技术面: {state.get("market_report", "")[:800]}

情绪面: {state.get("sentiment_report", "")[:500]}

新闻面: {state.get("news_report", "")[:500]}

基本面: {state.get("fundamentals_report", "")[:500]}
"""
                # 查询相似历史决策（最多3条），排除当天的记录
                historical_memories = decision_memory.get_memories(
                    current_situation,
                    n_matches=3,
                    exclude_date=trade_date  # 排除当天记录，避免当日多次分析时引用自己
                )

                if historical_memories:
                    previous_decision_reflection = _format_historical_decisions(historical_memories)
                    logger.info(f"找到 {len(historical_memories)} 条历史决策记录")
                else:
                    logger.info(f"股票 {ticker} 无历史决策记录")

            except Exception as e:
                logger.warning(f"查询历史决策失败: {e}")
                previous_decision_reflection = f"查询历史决策时出错: {str(e)}"

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

## 报告 8：上次决策反思（如有）

{previous_decision_reflection}

---

请根据以上报告，生成一份专业的综合投资研究报告。如果有上次决策反思，请在报告中体现对历史决策的回顾和经验教训的吸收。
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

        # ========== 2. 记录本次决策到 Memory ==========
        logger.info(f"[Memory] decision_memory is None: {decision_memory is None}")
        if decision_memory is not None:
            logger.info(f"[Memory] decision_memory type: {type(decision_memory)}")
            logger.info(f"[Memory] has add_decision_with_context: {hasattr(decision_memory, 'add_decision_with_context')}")
            try:
                # 构建当前市场情况摘要
                current_situation = f"""
股票: {ticker} {stock_name}
日期: {trade_date}

【技术面】
{state.get("market_report", "")[:1000]}

【情绪面】
{state.get("sentiment_report", "")[:800]}

【新闻面】
{state.get("news_report", "")[:800]}

【基本面】
{state.get("fundamentals_report", "")[:800]}

【最终决策】
{state.get("final_trade_decision", "")[:500]}
"""
                # 提取决策信息
                final_decision = state.get("final_trade_decision", "")
                decision_info = _extract_decision_info(final_decision, consolidation_report)
                logger.info(f"[Memory] decision_info extracted: {decision_info['decision_type']}")

                # 构建建议摘要
                recommendation = f"""
决策类型: {decision_info['decision_type']}
置信度: {decision_info['confidence']}
目标价: {decision_info.get('target_price', '未指定')}
止损价: {decision_info.get('stop_loss', '未指定')}
建议仓位: {decision_info.get('position_size', '未指定')}%

综合报告摘要:
{consolidation_report[:1500]}
"""
                # 使用 add_decision_with_context 记录（如果可用）
                if hasattr(decision_memory, 'add_decision_with_context'):
                    logger.info(f"[Memory] Calling add_decision_with_context...")
                    record_id = decision_memory.add_decision_with_context(
                        situation=current_situation,
                        recommendation=recommendation,
                        ticker=ticker,
                        decision_date=trade_date,
                        decision_type=decision_info['decision_type'],
                        confidence=decision_info['confidence'],
                        extra_context={
                            "stock_name": stock_name,
                            "target_price": decision_info.get('target_price'),
                            "stop_loss": decision_info.get('stop_loss'),
                            "position_size": decision_info.get('position_size'),
                        }
                    )
                    logger.info(f"✅ 决策已记录到 Memory: {record_id}")
                else:
                    # 使用基本的 add_situations 方法
                    logger.info(f"[Memory] Calling add_situations (fallback)...")
                    decision_memory.add_situations([(current_situation, recommendation)])
                    logger.info(f"✅ 决策已记录到 Memory (基本模式)")

            except Exception as e:
                import traceback
                logger.error(f"❌ 记录决策到 Memory 失败: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")

        return {
            "consolidation_report": consolidation_report
        }

    return consolidation_node
