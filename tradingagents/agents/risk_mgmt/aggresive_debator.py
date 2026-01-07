import time
import json
from tradingagents.agents.utils.state_utils import apply_risk_debate_limits


def create_risky_debator(llm):
    """
    创建趋势交易员(Momentum_Trader)辩论节点

    角色定位：专注于捕捉价格动量和技术形态突破机会的短线交易员
    核心关注：技术突破、量价配合、动量信号、板块联动、商品期货走势
    """
    def risky_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]

        # 应用历史长度限制，防止context window溢出
        risk_debate_state = apply_risk_debate_limits(risk_debate_state)

        history = risk_debate_state.get("history", "")
        risky_history = risk_debate_state.get("risky_history", "")

        current_safe_response = risk_debate_state.get("current_safe_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # 获取上次决策反思（如果有）
        prev_decision_reflection = state.get("previous_decision_reflection", "")
        reflection_context = ""
        if prev_decision_reflection and "首次分析" not in prev_decision_reflection and "无历史决策" not in prev_decision_reflection:
            reflection_context = f"""
【历史决策反思】（请务必参考）
{prev_decision_reflection}
请根据上述反思调整您的辩论策略。如果之前的决策错误，避免类似判断；如果正确，强化成功的分析逻辑。
"""

        prompt = f"""作为趋势交易员（Momentum Trader），您专注于捕捉价格动量和技术形态突破机会。

【角色定位】
- 交易风格：顺势而为，不抄底不摸顶
- 入场原则：突破确认后入场，跌破止损位出场
- 持仓周期：3-20个交易日
- 核心理念：趋势一旦形成，往往会延续比预期更长的时间

【您必须在辩论中引用以下数据支撑观点】

1. **技术形态数据**（来自market_report）:
   - 均线多头/空头排列状态
   - RSI/MACD的位置和交叉信号
   - 成交量变化趋势
   - 引用示例："均线呈多头排列，MACD金叉确认，趋势延续概率高"

2. **板块联动数据**（如market_report中有板块指数信息）:
   - 个股涨幅 vs 板块涨幅的相对强弱
   - 板块整体处于轮动的哪个阶段
   - 引用示例："个股近10日涨幅X%，跑赢板块Y个百分点，属于板块龙头"

3. **商品期货联动**（如market_report中有期货数据）:
   - 沪铜/沪金主力合约的趋势
   - 期货走强时，论证股价有进一步上涨空间
   - 引用示例："沪铜主力近30日上涨X%，对铜业龙头形成业绩利好"

4. **资金流向数据**（来自sentiment_report）:
   - 主力资金持续流入
   - 北向资金增持
   - 引用示例："主力资金连续X日净流入，趋势资金进场明显"

以下是交易员的决策方案：

{trader_decision}

【分析报告参考】
技术面与估值报告: {market_research_report}
资金面与情绪报告: {sentiment_report}
新闻与宏观报告: {news_report}
基本面报告: {fundamentals_report}

【当前辩论历史】
{history}

【价值投资者的观点】
{current_safe_response}

【风控官的观点】
{current_neutral_response}
{reflection_context}
【辩论任务】
1. 用技术面数据论证"趋势延续"的概率
2. 用板块强势和期货走势预判业绩弹性
3. 反驳价值投资者：等待估值回落可能踏空主升浪
4. 反驳风控官：波动不是风险，错过趋势才是最大风险
5. 强调：强趋势股的特点是"涨得比你想象的更高"

【信号冲突处理】
当遇到以下冲突信号时，请明确表明您的立场：
1. 技术看多 + 资金流出：
   - 优先信任技术形态，资金流出可能是主力洗盘
   - 但需设置更紧的止损位
2. 趋势向上 + 估值过高：
   - 估值是滞后指标，趋势股往往在高估值区间继续上涨
   - 用动量确认而非估值决定进出
3. 板块强势 + 个股滞涨：
   - 可能是补涨机会，也可能是弱势股
   - 需要观察成交量是否放大
4. 北向流入 + 主力流出：
   - 外资长线思维，主力可能短线调仓
   - 关注资金分歧持续时间

【注意】
- 如果其他观点尚未发言，只需陈述您的立场，不要虚构对方观点
- 必须引用具体数据支撑您的论点
- 使用中文，以对话方式输出，不需要特殊格式"""

        response = llm.invoke(prompt)

        argument = f"趋势交易员(Momentum Trader): {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risky_history + "\n" + argument,
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Risky",
            "current_risky_response": argument,
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return risky_node
