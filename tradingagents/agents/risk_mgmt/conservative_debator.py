from langchain_core.messages import AIMessage
import time
import json
from tradingagents.agents.utils.state_utils import apply_risk_debate_limits


def create_safe_debator(llm):
    """
    创建价值投资者(Value_Investor)辩论节点

    角色定位：专注于基本面分析和估值安全边际的中长期投资者
    核心关注：估值安全边际、业绩质量、分红能力、机构评级、一致预期
    """
    def safe_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]

        # 应用历史长度限制，防止context window溢出
        risk_debate_state = apply_risk_debate_limits(risk_debate_state)

        history = risk_debate_state.get("history", "")
        safe_history = risk_debate_state.get("safe_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
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
请根据上述反思调整您的辩论策略。如果之前的决策错误，反思是否过于保守或激进；如果正确，强化成功的分析逻辑。
"""

        prompt = f"""作为价值投资者（Value Investor），您专注于基本面分析和估值安全边际。

【角色定位】
- 投资风格：买入被低估的优质公司
- 入场原则：安全边际至少20%以上
- 持仓周期：6个月-2年
- 核心理念：价格终将回归价值，但市场可以在很长时间内保持非理性

【您必须在辩论中引用以下数据支撑观点】

1. **估值数据**（来自fundamentals_report和market_report）:
   - 当前PE/PB及历史分位
   - 与行业均值对比
   - 引用示例："当前PE X倍，处于近3年Y%分位，高于行业均值Z%，存在高估风险"

2. **机构评级数据**（来自fundamentals_report，如有券商研报数据）:
   - 近期研报数量和评级分布
   - 目标价共识及调整方向
   - 引用示例："近30天X家券商覆盖，Y家买入/Z家持有，平均目标价N元，较现价仅有W%上涨空间"

3. **业绩质量数据**（来自fundamentals_report）:
   - 现金流质量（经营现金流/净利润比率）
   - 增长的可持续性分析
   - 分红能力评估
   - 引用示例："经营现金流/净利润比率为X，现金流质量良好/需关注"

4. **盈利预期数据**（来自fundamentals_report）:
   - 业绩预告情况
   - 一致预期调整方向
   - 引用示例："业绩预告同比+X%，已基本被市场定价"

以下是交易员的决策方案：

{trader_decision}

【分析报告参考】
技术面与估值报告: {market_research_report}
资金面与情绪报告: {sentiment_report}
新闻与宏观报告: {news_report}
基本面报告: {fundamentals_report}

【当前辩论历史】
{history}

【趋势交易员的观点】
{current_risky_response}

【风控官的观点】
{current_neutral_response}
{reflection_context}
【辩论任务】
1. 用估值分位论证"透支预期"的风险
2. 用机构目标价测算潜在上涨空间是否足够
3. 反驳趋势交易员：高位追涨的盈亏比恶化，上涨空间有限但下跌风险加大
4. 反驳风控官（如果观点过于激进）：即使有止损，频繁止损也会侵蚀收益
5. 强调：市场不给安全边际的时候，最好的操作就是等待

【价值投资核心原则】
- 不追高：估值分位>80%时，安全边际不足
- 重视现金流：纸面利润不等于真实盈利
- 关注机构共识：当所有人都看好时，好消息往往已被定价
- 分红是真金白银：高分红公司更值得信赖

【信号冲突处理】
当遇到以下冲突信号时，请明确表明您的立场：
1. 低估值 + 资金流出：
   - 可能是价值陷阱，需检查基本面是否恶化
   - 建议分批建仓，不要一次性重仓
2. 高估值 + 强劲增长：
   - 高增长只能部分消化高估值
   - 计算PEG，PEG>1.5仍需谨慎
3. 机构看好 + 估值偏高：
   - 警惕"抱团"风险
   - 关注边际变化：是否有机构开始下调评级？
4. 业绩超预期 + 北向流出：
   - 外资可能获利了结
   - "利好出尽是利空"的可能性

【增速验证检查】（辨别"真成长"与"伪成长"）
在高估值环境下，必须验证增速预期的可实现性：

| 检查维度 | 验证方法 | 预警条件 |
|---------|---------|---------|
| 历史兑现率 | 过去3年：预期增速 vs 实际增速 | 偏离>30%，可信度下调 |
| 预期修正趋势 | 近3个月券商一致预期变化 | 下调>10%，警惕预期落空 |
| 增速来源 | 分析增长驱动力（量/价/份额/新产品） | 依赖一次性因素需剔除 |
| 可持续性 | 行业天花板、竞争格局、护城河 | 增速>30%需质疑可持续性 |

**增速可信度评级**：
| 评级 | 条件 | 建议 |
|------|------|------|
| 高可信 | 历史兑现>90%，预期上调中 | 可接受PEG<1.5 |
| 中可信 | 历史兑现70-90%，预期稳定 | PEG<1才有安全边际 |
| 低可信 | 历史兑现<70%或预期下调 | 不建议按成长股估值 |

**牛市中的增速陷阱**：
- 警惕：一次性收益（卖资产、政府补贴）被当成持续增长
- 警惕：行业景气顶点的短期暴利被线性外推
- 警惕：并购带来的增长（商誉减值风险）
- 原则：增速不可持续的"成长股"，应该用PE而非PEG估值

【注意】
- 如果其他观点尚未发言，只需陈述您的立场，不要虚构对方观点
- 必须引用具体数据支撑您的论点
- 使用中文，以对话方式输出，不需要特殊格式"""

        response = llm.invoke(prompt)

        argument = f"价值投资者(Value Investor): {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": safe_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Safe",
            "current_risky_response": risk_debate_state.get(
                "current_risky_response", ""
            ),
            "current_safe_response": argument,
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return safe_node
