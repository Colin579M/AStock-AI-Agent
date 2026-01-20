from langchain_core.messages import AIMessage
import time
import json
from tradingagents.agents.utils.state_utils import apply_invest_debate_limits
from tradingagents.agents.utils.rating_extractor import format_key_metrics_for_bear
from tradingagents.agents.utils.claim_extractor import (
    extract_claims_simple,
    mark_claims_addressed,
    format_rebuttal_section
)


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]

        # 应用历史长度限制，防止context window溢出
        investment_debate_state = apply_invest_debate_limits(investment_debate_state)

        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state.get("market_report", "")
        sentiment_report = state.get("sentiment_report", "")
        news_report = state.get("news_report", "")
        fundamentals_report = state.get("fundamentals_report", "")

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # 获取上次决策反思（如果有）
        prev_decision_reflection = state.get("previous_decision_reflection", "")
        reflection_context = ""
        if prev_decision_reflection and "首次分析" not in prev_decision_reflection and "无历史决策" not in prev_decision_reflection:
            reflection_context = f"""
**上次决策反思**（重要 - 从过往成败中学习）：
{prev_decision_reflection}
请在构建论据时参考此反思。若上次决策错误，识别被忽视的风险；若正确，强化已验证的风险因素。
"""

        # 提取基本面核心指标供空方回应
        key_metrics_for_bear = format_key_metrics_for_bear(fundamentals_report)

        # === 锁定反驳机制：获取待回应论点（多头提出的） ===
        pending_rebuttals = investment_debate_state.get("pending_rebuttals", [])
        rebuttal_section = format_rebuttal_section(pending_rebuttals, opponent="多头")

        prompt = f"""你是空头分析师，负责提出投资该股票的风险论据。
{rebuttal_section}

═══════════════════════════════════════════════════════════════
【跨语言思维链指令】Cross-Lingual Chain of Thought
═══════════════════════════════════════════════════════════════

**Step 1: Think in English** (Internal reasoning)
For risk analysis, valuation concerns, and logical argumentation:
- Use English to structure your bear case arguments
- Apply universal frameworks: Margin of safety, risk-reward ratio, probability of loss
- Ensure logical consistency in risk quantification

**Step 2: Preserve A-share Context** (Domain knowledge)
以下内容必须用中文理解，不可英文化：
- 估值陷阱：商誉减值、资产注水、关联交易
- 制度风险：质押平仓、解禁压力、大宗交易折价
- 市场特征：抱团瓦解、游资撤退、北向资金流出
- 周期判断：周期顶部、产能过剩、库存高企

**Step 3: Output in Chinese** (Final response)
- 使用中文输出最终分析，保留A股特有术语
- 论据清晰，数据支撑，回应基本面核心发现

═══════════════════════════════════════════════════════════════

================================================================================
【论据质量要求】（强制执行）
================================================================================

你的每个论据必须满足以下任一条件：

1. **数据支撑**：引用具体数字
   - 正确示例："负债率从30%升至50%，存在偿债压力"
   - 错误示例："可能存在财务风险"

2. **可验证事实**：引用公开信息（财报、公告、新闻）
   - 正确示例："根据年报，应收账款周转天数从45天延长至78天"
   - 错误示例："应收账款可能有问题"

3. **逻辑推理**：基于行业规律的合理推断（需说明推断依据）
   - 正确示例："煤炭行业周期下行，参考2015年周期低谷PE降至5倍"
   - 错误示例："行业可能不好"

❌ **禁止以下论据类型**：
- "可能存在风险" → 必须具体化
- "市场情绪不好" → 必须有数据佐证
- 纯猜测性陈述

================================================================================
【必须回应基本面报告核心发现】
================================================================================

{key_metrics_for_bear}

你必须对上述发现给出明确回应：
- 若**同意**基本面分析结论，说明认可理由
- 若**反驳**，必须提供数据或逻辑依据，说明基本面分析的哪些假设可能有误

================================================================================
【缺失数据处理】
================================================================================

若你的论据依赖于缺失数据，必须：
1. 明确标注："⚠️ 依赖缺失数据：XXX"
2. 说明该数据的重要性权重（高/中/低）
3. 说明若该数据证实你的担忧，影响有多大

================================================================================
【可用资源】
================================================================================

- 技术面报告：{market_research_report}
- 情绪面报告：{sentiment_report}
- 消息面报告：{news_report}
- 基本面报告：{fundamentals_report}
- 辩论历史：{history}
- 多头最新论点：{current_response}
- 历史教训：{past_memory_str if past_memory_str.strip() else "无相关历史教训"}
{reflection_context}

================================================================================
【输出要求】
================================================================================

请提出有理有据的空头论点，包含：

1. **风险与挑战**：具体量化的风险点
2. **竞争劣势**：有数据支撑的竞争力分析
3. **负面指标**：财务/技术/情绪面的具体警示信号
4. **反驳多头**：针对多头论点的具体反驳（必须有数据或逻辑支撑）
5. **对基本面核心发现的回应**：同意或反驳盈亏比/安全边际/目标价

以对话式风格呈现，直接与多头论点辩论：
"""

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        # === 锁定反驳机制：论点追踪 ===
        # 1. 提取本轮我方论点
        my_claims = extract_claims_simple(response.content, max_claims=3)

        # 2. 检查我是否回应了pending claims（多头提出的）
        pending = investment_debate_state.get("pending_rebuttals", [])
        addressed = investment_debate_state.get("addressed_claims", [])
        still_pending, newly_addressed = mark_claims_addressed(pending, response.content)

        # 3. 获取现有的claims列表
        existing_bull_claims = investment_debate_state.get("bull_claims", [])
        existing_bear_claims = investment_debate_state.get("bear_claims", [])

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
            # === 锁定反驳机制：更新论点追踪 ===
            "bull_claims": existing_bull_claims,  # 保持多头论点不变
            "bear_claims": existing_bear_claims + my_claims,  # 累加我方论点
            "pending_rebuttals": my_claims,  # 我的新论点成为多头的待回应项
            "addressed_claims": addressed + newly_addressed,  # 累加已回应论点
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
