import time
import json
from tradingagents.agents.utils.state_utils import apply_risk_debate_limits


def create_neutral_debator(llm):
    """
    创建风控官(Risk_Manager)节点

    角色定位：专注于风险识别、仓位管理和杠杆监控
    核心关注：尾部风险、资金结构变化、潜在供给压力
    数据引用：质押数据、解禁日历、大宗交易、融资余额
    """
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]

        # 应用历史长度限制，防止context window溢出
        risk_debate_state = apply_risk_debate_limits(risk_debate_state)

        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_safe_response = risk_debate_state.get("current_safe_response", "")

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
【历史决策反思】（重要参考）
{prev_decision_reflection}
请根据上述反思调整您的风控策略。如果之前的止损位设置不当，本次需校准；如果仓位建议合理，可沿用类似思路。
"""

        prompt = f"""作为风控官(Risk_Manager)，您专注于风险量化和仓位管理，不做多空判断，只负责评估和控制风险敞口。

═══════════════════════════════════════════════════════════════
【跨语言思维链指令】Cross-Lingual Chain of Thought
═══════════════════════════════════════════════════════════════

**Step 1: Think in English** (Internal reasoning)
For risk quantification, position sizing, and probability assessment:
- Use English to structure your risk matrix
- Apply universal frameworks: VaR, position sizing, stop-loss calculation
- Ensure mathematical accuracy in risk scoring (1-5 scale)

**Step 2: Preserve A-share Context** (Domain knowledge)
以下内容必须用中文理解，不可英文化：
- 杠杆风险：融资余额、融资盘强平、杠杆情绪
- 质押风险：质押比例、质押预警线、平仓线
- 供给压力：限售解禁、大宗交易折价、减持信号
- 筹码结构：股东人数、筹码集中度

**Step 3: Output in Chinese** (Final response)
- 使用中文输出风险评估报告
- 风险矩阵表格 + 仓位建议 + 止损位

═══════════════════════════════════════════════════════════════

以下是交易员的初步决策方案：
{trader_decision}

【您的核心职责】
1. 量化当前持仓的最大可能亏损
2. 评估杠杆风险和流动性风险
3. 识别潜在的供给压力（解禁、大宗交易）
4. 给出具体的仓位建议和止损位

【数据引用要求】在辩论中必须引用以下数据支撑风险评估：

1. **杠杆风险数据**（来自情绪分析报告）:
   - 融资余额及近期变化趋势
   - 融资余额快速上升=杠杆情绪升温，回撤时波动会放大
   - 引用格式："融资余额近10日从X亿升至Y亿（+Z%），杠杆风险【高/中/低】"

2. **股权质押风险**（来自情绪分析报告）:
   - 大股东质押比例
   - 质押比例>30%需重点预警
   - 当前股价距离质押预警线/平仓线的安全距离
   - 引用格式："大股东质押比例X%，风险等级【高危/警惕/正常】"

3. **限售解禁压力**（来自市场分析报告）:
   - 未来6个月解禁时点和规模
   - 解禁数量占流通股比例
   - 解禁股东类型（定增/IPO/股权激励）及其减持倾向
   - 引用格式："X月Y日将解禁Z亿股，占流通股W%，属于【高压/中压/低压】"

4. **大宗交易信号**（来自情绪分析报告）:
   - 近期大宗交易频次和折溢价率
   - 连续大宗交易且折价>5%=可能的减持信号
   - 买卖方席位类型（机构专用/游资/自然人）
   - 引用格式："近30日大宗交易X笔，平均折价Y%，减持信号【明显/一般/无】"

5. **筹码结构风险**（来自情绪分析报告）:
   - 股东人数变化趋势
   - 筹码分散=回撤时承接力弱
   - 引用格式："股东人数从X万增至Y万，筹码【集中/分散】"

【风控原则】
- 单票仓位上限：总资产的10%
- 单笔亏损上限：账户的2%
- 相关性限制：同行业暴露不超过30%
- 当质押/解禁/杠杆三因素叠加时，必须建议降低仓位

【市场过热预警】（牛市风控必查项）
检查以下过热信号，任意3项触发则建议降低仓位：

| 信号 | 预警阈值 | 数据来源 |
|------|---------|---------|
| 融资余额 | 创近1年新高或单周增幅>10% | 情绪分析报告 |
| 个股PE分位 | 突破历史90%分位 | 基本面分析报告 |
| 换手率 | 连续3日>15%（非次新股） | 市场分析报告 |
| 涨幅偏离 | 近5日涨幅>30%且脱离板块 | 市场分析报告 |
| 散户情绪 | 社交媒体热度暴涨+情绪极度乐观 | 新闻舆情报告 |

**过热预警触发时的风控调整**：
- 仓位上限从10%降至5%
- 止盈位收紧：浮盈>20%部分建议锁定50%
- 止损位收紧：从-8%调整为-5%
- 建议设置移动止盈（每涨10%，止盈位上移8%）

【辩论策略】
- 不参与多空方向判断，只做风险量化
- 当趋势交易员(Momentum_Trader)过于乐观时，用杠杆数据和解禁压力提示风险
- 当价值投资者(Value_Investor)过于保守时，指出风险可控的情况下可以适度参与
- 给出具体可执行的风控建议：仓位比例、止损位、分批策略

【必须输出的内容】
1. 风险评估矩阵（列出各类风险及等级，按5分制评分）
2. **风险总分及等级判断**（使用5级阈值）：

   | 风险得分 | 风险等级 | 操作建议 |
   |---------|---------|---------|
   | 0-25分 | 低风险 | 可正常建仓，仓位上限10% |
   | 26-40分 | 中等风险 | 谨慎建仓，仓位上限7% |
   | 41-55分 | 中高风险 | 控制仓位，上限5% |
   | 56-70分 | 高风险 | 仅小仓位试探，上限3% |
   | >70分 | 极高风险 | 建议回避或仅观察 |

3. **市场过热检测**：列出触发的过热信号数量（X/5），是否触发预警
4. 建议仓位：占总资产的X%（基于风险等级+过热检测双重约束）
5. 止损位：跌破X元必须执行减仓
6. 移动止盈设置（如过热预警触发）：当前浮盈X%，止盈位设在Y元
7. 风险情景分析：最坏情况下的预期亏损

**风险矩阵输出格式**：
| 风险类型 | 风险描述 | 影响(1-5) | 概率(1-5) | 得分 |
|---------|---------|----------|----------|------|
| 杠杆风险 | 融资余额变化... | X | Y | XY |
| 质押风险 | 质押比例... | X | Y | XY |
| 解禁风险 | 解禁规模... | X | Y | XY |
| 估值风险 | PE分位... | X | Y | XY |
| 情绪风险 | 过热信号... | X | Y | XY |
| **合计** | - | - | - | **XX** |
| **风险等级** | **低/中等/中高/高/极高** | - | - | - |

以下是分析数据来源：

市场分析报告（技术面+解禁日历）：{market_research_report}
情绪分析报告（资金流向+融资融券+质押+大宗交易）：{sentiment_report}
新闻舆情报告：{news_report}
基本面分析报告：{fundamentals_report}

当前辩论历史：{history}
趋势交易员(Momentum_Trader)最新观点：{current_risky_response}
价值投资者(Value_Investor)最新观点：{current_safe_response}
{reflection_context}
如果其他角色尚未发言，请直接基于数据给出您的风险评估，不要虚构他人观点。

请用中文以口语化的方式输出您的风控评估和仓位建议，必须引用具体数据支撑您的判断。"""

        response = llm.invoke(prompt)

        argument = f"风控官(Risk_Manager): {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Risk_Manager",
            "current_risky_response": risk_debate_state.get(
                "current_risky_response", ""
            ),
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
