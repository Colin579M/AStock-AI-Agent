import time
import json
from tradingagents.agents.utils.rating_extractor import (
    format_analyst_ratings_summary,
    extract_rating_from_fundamentals_report,
    extract_rating_from_market_report,
)


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # 提取分析师评级汇总
        analyst_ratings_summary = format_analyst_ratings_summary(
            market_research_report,
            fundamentals_report,
            news_report,
            sentiment_report
        )

        # 提取基本面核心评级用于一致性检查
        fundamentals_rating = extract_rating_from_fundamentals_report(fundamentals_report)
        market_rating = extract_rating_from_market_report(market_research_report)

        prompt = f"""作为投资组合经理和辩论主持人，你需要综合评估多空辩论并做出最终决策。

═══════════════════════════════════════════════════════════════
【跨语言思维链指令】Cross-Lingual Chain of Thought
═══════════════════════════════════════════════════════════════

**Step 1: Think in English** (Internal reasoning)
For consistency checking, logical evaluation, and final decision:
- Use English to structure your evaluation framework
- Apply logical checks: Does Bull case address Bear concerns? Does risk assessment align with position sizing?
- Ensure consistency between analyst ratings and debate conclusions

**Step 2: Preserve A-share Context** (Domain knowledge)
以下内容必须用中文理解，不可英文化：
- 市场情绪：抱团、游资炒作、国家队护盘
- 制度风险：质押爆仓、解禁压力、融资盘强平
- 投资术语：龙头首阴、板块轮动、周期底部

**Step 3: Output in Chinese** (Final response)
- 使用中文输出最终投资建议
- 评级汇总表 + 分歧分析 + 触发条件 + 投资计划

═══════════════════════════════════════════════════════════════

================================================================================
【输入汇总】
================================================================================

{analyst_ratings_summary}

**多空辩论历史**：
{history}

**历史教训**：
{past_memory_str if past_memory_str.strip() else "无相关历史教训"}

================================================================================
【一致性检查规则】（强制执行）
================================================================================

基本面分析师评级：{fundamentals_rating.get('rating', '未明确')}
技术面分析师评级：{market_rating.get('rating', '未明确')}

**规则1**：若基本面/技术面分析师报告结论为"买入"但你的最终决策为"HOLD/SELL"，必须：
1. 明确列出分歧点（哪些新增信息改变了判断）
2. 说明采纳辩论结论而非分析师报告的原因
3. 给出升级至BUY的触发条件

**规则2**：若分析师报告结论为"卖出"但你的最终决策为"BUY/HOLD"，必须：
1. 说明空方论据为何不成立
2. 给出降级至SELL的触发条件

================================================================================
【辩论质量审核】
================================================================================

审核空方论据是否满足以下要求：
- [ ] 基于数据或可验证的事实（非纯猜测）
- [ ] 回应了基本面报告的核心发现（如盈亏比、安全边际）
- [ ] 若引用缺失数据，已说明该数据的重要性权重

若空方论据不满足要求，在输出中标注：
⚠️ 空方论据质量：[合格/存疑]，原因：...

================================================================================
【输出格式要求】（严格遵守）
================================================================================

你的回答必须包含以下结构化内容：

## 评级汇总

| 来源 | 评级 | 核心理由 |
|------|------|----------|
| 技术面分析师 | XX | ... |
| 基本面分析师 | XX | ... |
| 多头辩论 | XX | ... |
| 空头辩论 | XX | ... |
| **最终采纳** | **XX** | ... |

## 分歧分析（若有分歧必填）

若最终决策与分析师报告结论不一致，必须填写：
- 分歧点1：...
- 分歧点2：...
- 采纳理由：...

## 空方论据质量评估

⚠️ 空方论据质量：[合格/存疑]
- 评估依据：...

## 升级/降级触发条件

- 升级至BUY条件：...
- 降级至SELL条件：...

## 投资计划

- **建议**：BUY/HOLD/SELL
- **信心度**：高/中/低
- **仓位建议**：XX%
- **入场策略**：...
- **止损位**：...
- **理由摘要**：...

================================================================================
【决策原则】
================================================================================

1. 不要因为"两边都有道理"就默认HOLD，必须基于最强论据做出决策
2. 重视基本面盈亏比分析，这是量化风险收益的核心指标
3. 若空方论据无数据支撑，应降低其权重
4. 历史教训是重要参考，避免重复过去的错误
"""
        response = llm.invoke(prompt)

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
