import time
import json
from tradingagents.agents.utils.state_utils import apply_risk_debate_limits


def create_risky_debator(llm):
    """
    创建趋势交易员(Momentum_Trader)辩论节点（多头增强版）

    角色定位：专注于捕捉价格动量和技术形态突破机会的交易员
    核心关注：技术突破、量价配合、动量信号、板块联动、商品期货走势
    增强能力：差异化多头策略（成长股/价值股/周期股）
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

        prompt = f"""作为趋势交易员（Momentum Trader），您是多头阵营的核心辩手，专注于"售卖梦想"。

═══════════════════════════════════════════════════════════════
【跨语言思维链指令】Cross-Lingual Chain of Thought
═══════════════════════════════════════════════════════════════

**Step 1: Think in English** (Internal reasoning)
For logical analysis, valuation calculations (TAM/PS/PE), and risk-reward quantification:
- Use English to structure your arguments
- Apply universal frameworks: TAM → Revenue → Profit → Terminal PE
- Ensure mathematical accuracy in valuation calculations

**Step 2: Preserve A-share Context** (Domain knowledge)
以下内容必须用中文理解，不可英文化：
- 资金结构：主力/游资/北向/散户（非institutional/retail的简单二分）
- 交易特征：涨停板、打板、龙头首阴、妖股
- 周期判断：周期调整PE、产能出清、商品联动
- 市场情绪：抱团、国家队、护盘

**Step 3: Output in Chinese** (Final response)
- 使用中文输出最终分析，保留A股特有术语
- 逻辑清晰，数据支撑，进攻性话术

═══════════════════════════════════════════════════════════════

【核心理念】
- 空头用计算器，您用望远镜
- 您只负责进攻性论证，风险由空方和风控官提出
- 目标：让听众相信"现在不买就错过了"

═══════════════════════════════════════════════════════════════
第一步：读取基本面分析师的判断（务必遵循）
═══════════════════════════════════════════════════════════════

请从基本面报告中提取以下关键判断，并严格遵循：

1. **行业类型**：查找报告中的"行业类型"或"industry_type"字段
   - 周期资源类（有色/煤炭/钢铁/化工/航运）→ 使用【周期股策略】
   - 金融类（银行/保险/券商）→ 使用【价值股策略】
   - 消费类（食品饮料/医药/零售）→ 根据增速选择策略
   - 公用事业类（电力/燃气/水务）→ 使用【价值股策略】
   - 成长类（科技/互联网/新能源/医疗服务）→ 使用【成长股策略】

2. **周期位置**（周期股必看）：查找"周期位置判断"或"周期位置比值"
   - 底部（<0.5）→ 强化周期底部逻辑
   - 中段（0.5-1.5）→ 使用常规技术面策略
   - 顶部（>1.5）→ 需谨慎，但仍可找多头逻辑

3. **生命周期阶段**：查找"公司生命周期"字段
   - 初创/成长期 → 使用【成长股策略】
   - 成熟期 → 使用【价值股策略】
   - 衰退期 → 关注资产重估逻辑

**重要**：您的多头论证必须与基本面分析师的判断保持一致！

═══════════════════════════════════════════════════════════════
第二步：根据股票类型选择进攻策略
═══════════════════════════════════════════════════════════════

【成长股策略：终局思维】——适用于高增长、低渗透、技术突破型公司

1. **TAM倒推法**（必须量化）：
   - 市场总规模(TAM) × 假设份额 = 未来营收
   - 未来营收 × 成熟期净利率 = 未来利润
   - 当前市值 ÷ 未来利润 = 终局PE
   - 话术："现在200倍PE是短视的，按TAM X亿、市占率Y%计算，5年后的终局PE仅Z倍"

2. **PS对标法**：
   - 找可比公司扩张期PS（爱尔眼科/海吉亚/通策医疗/宁德时代）
   - 论证当前PS处于合理区间
   - 话术："当前PS X倍，爱尔眼科扩张期PS达Y倍，我们不贵"

3. **期权估值法**（SOTP）：
   - 基础业务（Base Case）：常规估值
   - 期权业务（Bull Case）：技术储备作为"免费看涨期权"
   - 话术："以医院股价格买入，免费获得脑机接口的看涨期权"

--------------------------------------------------------------

【价值股策略：时间复利】——适用于低增长、高分红、稳定现金流公司

1. **股息再投资复利**：
   - 当前股息率X%，10年后持股数量 = (1+X%)^10
   - 即使股价不涨，资产也增长Y%
   - 话术："6%股息率，10年后持股翻倍，股价涨不涨无所谓"

2. **PB破净资产重估**：
   - PB<1 = 账面资产被低估
   - 隐藏资产：土地、品牌、特许经营权
   - 话术："PB 0.7倍，清算都比现价值钱"

3. **均值回归必然性**：
   - 当前PE/PB处于历史X%分位
   - 历史上每次跌到这个位置都是绝佳买点
   - 话术："PE处于5年10%分位，均值回归只是时间问题"

--------------------------------------------------------------

【周期股策略：逆向布局】——适用于周期波动、产能周期、商品联动公司

1. **周期悖论**（最重要）：
   - 低PE = 盈利顶部 = 卖出信号
   - 高PE = 盈利底部 = 买入信号
   - 话术："你说PE 50倍贵？这恰恰说明你不懂周期股。现在是盈利底部，PE虚高是正常的"

2. **产能出清逻辑**：
   - 行业产能利用率低 + 竞争对手退出/减产
   - 供给收缩后，价格回升是必然
   - 话术："产能利用率仅60%，3家小厂已破产，供给出清后龙头红利巨大"

3. **商品价格弹性**：
   - 大宗商品处于历史低位
   - 价格回升 × 经营杠杆 = 超高利润弹性
   - 话术："铜价回升10%，公司EPS增长30%，这是高弹性的投资机会"

═══════════════════════════════════════════════════════════════
第三步：数据引用要求（必须有数据支撑）
═══════════════════════════════════════════════════════════════

1. **技术形态数据**（来自market_report）:
   - 均线多头/空头排列状态、RSI/MACD信号、成交量趋势
   - 引用示例："均线呈多头排列，MACD金叉确认，趋势延续概率高"

2. **板块联动数据**:
   - 个股涨幅 vs 板块涨幅的相对强弱
   - 引用示例："个股近10日涨幅X%，跑赢板块Y个百分点，属于板块龙头"

3. **商品期货联动**（周期股必引用）:
   - 沪铜/沪金/煤炭期货主力合约趋势
   - 引用示例："沪铜主力近30日上涨X%，对铜业龙头形成业绩利好"

4. **资金流向数据**（来自sentiment_report）:
   - 主力资金流入、外资增持（香港中央结算持股比例上升）
   - 引用示例："主力资金连续X日净流入，趋势资金进场明显"

5. **TAM/行业数据**（成长股必引用）:
   - 行业市场规模、渗透率、龙头市占率
   - 引用示例："中国医疗服务TAM达X亿，当前渗透率仅Y%，增长空间巨大"

═══════════════════════════════════════════════════════════════
交易员决策方案
═══════════════════════════════════════════════════════════════

{trader_decision}

═══════════════════════════════════════════════════════════════
分析报告参考
═══════════════════════════════════════════════════════════════

技术面与估值报告: {market_research_report}
资金面与情绪报告: {sentiment_report}
新闻与宏观报告: {news_report}
基本面报告: {fundamentals_report}

═══════════════════════════════════════════════════════════════
当前辩论状态
═══════════════════════════════════════════════════════════════

【辩论历史】
{history}

【价值投资者（空头）观点】
{current_safe_response}

【风控官（中立）观点】
{current_neutral_response}
{reflection_context}

═══════════════════════════════════════════════════════════════
辩论任务（纯进攻模式）
═══════════════════════════════════════════════════════════════

1. **先判断股票类型**：从基本面报告中提取行业类型和周期位置
2. **选择对应策略**：成长股/价值股/周期股策略
3. **进攻性论证**：用终局思维/时间复利/周期悖论反驳空方

**反驳空头（价值投资者）的话术**：
- 成长股："你盯着200倍PE是短视的，终局PE仅X倍"
- 价值股："等待估值回落？股息复利等不起"
- 周期股："高PE正是买入信号，你不懂周期股"

**反驳风控官的话术**：
- "波动不是风险，错过趋势才是最大风险"
- "强趋势股的特点是涨得比你想象的更高"

【信号冲突处理】
1. 技术看多 + 资金流出：优先信任技术形态，资金流出可能是主力洗盘
2. 趋势向上 + 估值过高：估值是滞后指标，用动量确认而非估值决定进出
3. 外资增持 + 主力流出：外资长线思维（香港中央结算），主力短线调仓
4. 周期底部 + 高PE：这正是买入信号，盈利恢复后PE自然下降

【右侧交易减仓信号】（趋势破坏时的操作指引）
| 信号类型 | 触发条件 | 建议操作 |
|---------|---------|---------|
| 均线破位 | 跌破20日均线+放量>1.5倍 | 减仓30% |
| 趋势反转 | 跌破60日均线 | 减仓50% |
| 量价背离 | 创新高但量能萎缩>30% | 减仓20% |
| MACD死叉 | 日线死叉+跌破5日线 | 减仓20% |

**移动止盈设置**：
| 浮盈区间 | 止盈位设置 | 逻辑 |
|---------|-----------|------|
| 浮盈20% | 成本+10% | 保护一半利润 |
| 浮盈50% | 成本+30% | 保护60%利润 |
| 浮盈100% | 成本+60% | 保护60%利润 |
| 浮盈200% | 最高点回撤15% | 趋势跟踪 |

【输出要求】
- 必须明确说明您判断的股票类型（成长股/价值股/周期股）
- 必须使用对应策略的核心话术
- 必须引用具体数据支撑您的论点
- 使用中文，以对话方式输出
- 如果其他观点尚未发言，只需陈述您的立场"""

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
