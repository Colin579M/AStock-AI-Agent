from langchain_core.messages import AIMessage
import time
import json
from tradingagents.agents.utils.state_utils import apply_invest_debate_limits
from tradingagents.agents.utils.claim_extractor import (
    extract_claims_simple,
    mark_claims_addressed,
    format_rebuttal_section
)


def create_bull_researcher(llm, memory):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]

        # 应用历史长度限制，防止context window溢出
        investment_debate_state = apply_invest_debate_limits(investment_debate_state)

        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

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
Previous decision reflection (IMPORTANT - learn from past mistakes/successes):
{prev_decision_reflection}
Consider this reflection when building your argument. If the previous decision was wrong, avoid similar mistakes. If it was right, reinforce similar reasoning.
"""

        # === 锁定反驳机制：获取待回应论点 ===
        pending_rebuttals = investment_debate_state.get("pending_rebuttals", [])
        rebuttal_section = format_rebuttal_section(pending_rebuttals, opponent="空方")

        prompt = f"""You are a Bull Analyst advocating for investing in the stock. Your task is to build a strong, evidence-based case emphasizing growth potential, competitive advantages, and positive market indicators.
{rebuttal_section}

═══════════════════════════════════════════════════════════════
【Cross-Lingual Chain of Thought】跨语言思维链
═══════════════════════════════════════════════════════════════

**Step 1: Think in English** (Internal reasoning)
For logical analysis, valuation frameworks, and argumentation structure:
- Use English to build your investment thesis
- Apply universal frameworks: TAM analysis, competitive moat, growth drivers
- Structure arguments logically with clear evidence chains

**Step 2: Preserve A-share Context** (Domain knowledge)
When referencing these A-share specific concepts, keep them in Chinese context:
- Capital flow: 主力资金, 游资, 北向资金 (NOT just "institutional flow")
- Trading patterns: 涨停板, 龙头, 板块轮动
- Valuation quirks: 周期调整PE, 商誉减值
- Market sentiment: 抱团, 国家队护盘

**Step 3: Output in Chinese** (Final response)
- 使用中文输出最终分析
- 保留A股特有术语，不做翻译

═══════════════════════════════════════════════════════════════

Key points to focus on:
- Growth Potential: Highlight the company's market opportunities, revenue projections, and scalability.
- Competitive Advantages: Emphasize factors like unique products, strong branding, or dominant market positioning.
- Positive Indicators: Use financial health, industry trends, and recent positive news as evidence.
- Bear Counterpoints: Critically analyze the bear argument with specific data and sound reasoning, addressing concerns thoroughly and showing why the bull perspective holds stronger merit.
- Engagement: Present your argument in a conversational style, engaging directly with the bear analyst's points and debating effectively rather than just listing data.

Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history of the debate: {history}
Last bear argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}
{reflection_context}
Use this information to deliver a compelling bull argument, refute the bear's concerns, and engage in a dynamic debate that demonstrates the strengths of the bull position. You must also address reflections and learn from lessons and mistakes you made in the past.
"""

        response = llm.invoke(prompt)

        argument = f"Bull Analyst: {response.content}"

        # === 锁定反驳机制：论点追踪 ===
        # 1. 提取本轮我方论点
        my_claims = extract_claims_simple(response.content, max_claims=3)

        # 2. 检查我是否回应了pending claims
        pending = investment_debate_state.get("pending_rebuttals", [])
        addressed = investment_debate_state.get("addressed_claims", [])
        still_pending, newly_addressed = mark_claims_addressed(pending, response.content)

        # 3. 获取现有的claims列表
        existing_bull_claims = investment_debate_state.get("bull_claims", [])
        existing_bear_claims = investment_debate_state.get("bear_claims", [])

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
            # === 锁定反驳机制：更新论点追踪 ===
            "bull_claims": existing_bull_claims + my_claims,  # 累加我方论点
            "bear_claims": existing_bear_claims,  # 保持对方论点不变
            "pending_rebuttals": my_claims,  # 我的新论点成为对方的待回应项
            "addressed_claims": addressed + newly_addressed,  # 累加已回应论点
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
