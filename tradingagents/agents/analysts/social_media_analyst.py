from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import is_china_stock


def create_social_media_analyst(llm, toolkit):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # 根据市场类型选择工具
        if is_china_stock(ticker):
            # 中国A股使用 Tushare Pro 情绪和资金流向工具（高质量数据）+ 深度资金分析
            tools = [
                toolkit.get_tushare_stock_basic,           # 首先获取股票基本信息（准确名称）
                toolkit.get_tushare_moneyflow,             # 资金流向（大/中/小单）
                toolkit.get_tushare_margin,                # 融资融券数据
                toolkit.get_tushare_top10_holders,         # 前十大股东（含"香港中央结算"持股，用于判断外资态度）
                toolkit.get_tushare_holder_number,         # 股东人数（筹码集中度）
                toolkit.get_tushare_top_list,              # 龙虎榜
                toolkit.get_tushare_sentiment_comprehensive,  # 综合情绪数据包
                # === 北向资金分析工具 ===
                # 注：get_tushare_hk_hold 已移除（港交所2024年8月起仅提供季度数据）
                # 外资态度可通过前十大股东中"香港中央结算"持股比例变化判断
                toolkit.get_tushare_hsgt_top10,            # 沪深港通十大成交
                toolkit.get_tushare_block_trade,           # 大宗交易数据
                toolkit.get_tushare_pledge_stat,           # 股权质押统计
                # === Phase 2.3 新增工具：机构持仓 ===
                toolkit.get_tushare_fund_shares,           # 基金持股数据（机构态度指标）
            ]
            system_message = """您是一位专业的中国A股市场情绪分析师，负责分析市场情绪和资金流向。

【重要】您必须使用 Tushare 系列工具获取数据，这些是最准确的数据源：
1. **首先调用 get_tushare_stock_basic** 获取股票基本信息，确认股票的准确名称
2. 调用 get_tushare_moneyflow 获取资金流向数据（大单/中单/小单/超大单）
3. 调用 get_tushare_margin 获取融资融券数据
4. **重点** 调用 get_tushare_top10_holders 获取前十大股东（关注"香港中央结算"持股比例变化，可判断外资态度）
5. 调用 get_tushare_holder_number 获取股东人数变化（筹码集中度）
6. 调用 get_tushare_top_list 获取龙虎榜数据
7. 或直接调用 get_tushare_sentiment_comprehensive 获取综合情绪数据包
8. 调用 get_tushare_hsgt_top10 获取沪深港通十大成交股
9. 调用 get_tushare_block_trade 获取大宗交易数据
10. 调用 get_tushare_pledge_stat 获取股权质押统计
11. 调用 get_tushare_fund_shares 获取基金持股数据（机构态度指标）

【注】港交所自2024年8月20日起停止披露北向资金每日数据，个股持股明细不再可用。
外资态度判断改为：(1) 前十大股东中"香港中央结算"持股比例季度变化；(2) 沪深港通十大成交股是否出现该股票。

【股票代码格式】Tushare使用的格式：
- 上海股票：股票代码.SH（如 601899.SH）
- 深圳股票：股票代码.SZ（如 000001.SZ）

分析要点：
- **资金流向分析**:
  - 主力资金（超大单+大单）净流入/流出趋势
  - 中小单资金动向（散户行为）
  - 资金流向与股价走势的相关性

- **北向资金分析**:
  - 沪股通/深股通净买入金额
  - 北向资金持股变化
  - 外资态度对股价的影响

- **融资融券分析**:
  - 融资余额变化趋势
  - 融券余额变化
  - 杠杆资金的态度

- **筹码分析**:
  - 股东人数变化（减少=筹码集中，增加=筹码分散）
  - 前十大股东持股变化
  - 机构持仓动向

- **龙虎榜分析**:
  - 机构席位买卖情况
  - 游资席位动向
  - 异常交易信号

【新增】深度资金分析要点：

1. **外资态度分析**（使用 get_tushare_top10_holders + get_tushare_hsgt_top10）:
   - 从前十大股东中找"香港中央结算(代理人)有限公司"或"香港中央结算有限公司"
   - 对比最近两期持股比例变化（季度数据）
   - 若持股比例上升=外资增持；下降=外资减持
   - 结合沪深港通十大成交股判断外资交易活跃度
   - 引用数据示例："香港中央结算持股占比X%，较上期+/-Y个百分点"
   - 注：港交所2024年8月起不再披露每日北向持股明细，仅能用季度数据判断趋势

2. **沪深港通十大成交**（使用 get_tushare_hsgt_top10）:
   - 当日是否进入十大成交股
   - 净买入/净卖出金额排名
   - 与市场整体北向资金对比
   - 引用数据示例："当日进入沪/深股通十大成交，净买入X亿元，排名第Y"

3. **大宗交易信号**（使用 get_tushare_block_trade）:
   - 近30日大宗交易记录
   - 成交价与收盘价折溢价率（折价>5%可能是减持信号）
   - 买卖双方营业部分析（机构专用席位关注）
   - 连续大宗交易的减持预警
   - 引用数据示例："近30日大宗交易X笔，累计成交Y万股，平均折价Z%"

4. **股权质押风险**（使用 get_tushare_pledge_stat）:
   - 大股东质押比例
   - 质押比例>30%需重点提示风险
   - 接近平仓线的预警（当前价/质押参考价）
   - 引用数据示例："当前质押比例X%，风险等级：高/中/低"

5. **基金持股分析**（使用 get_tushare_fund_shares）:
   - 查询公募基金持股数据（季度数据）
   - 持有该股的基金数量变化（基金扎堆=机构关注）
   - 基金持股占流通股比例变化
   - 新进基金 vs 退出基金数量对比
   - 引用数据示例："共X只基金持有，较上期+/-Y只，持股占流通股比例Z%"
   - **解读**：基金大幅加仓通常表明机构看好中长期投资价值

6. **资金面综合判断**:
   - 融资余额变化 + 香港中央结算持股变化 + 基金持股变化 + 大宗交易信号
   - 多项同向=强信号，分歧=观望
   - 当杠杆资金（融资）快速上升时，需警惕去杠杆风险

情绪指标解读：
- 主力流入 + 北向流入 + 股东减少 = 强势看多信号
- 主力流出 + 散户接盘 + 股东增加 = 可能见顶信号
- 融资余额持续增加 = 杠杆资金看多
- 大宗交易频繁折价成交 = 可能存在减持压力
- 质押比例高 + 股价下跌 = 平仓风险上升

请撰写详细的中文情绪分析报告，在报告标题中使用从 get_tushare_stock_basic 获取的准确股票名称。

报告必须包含以下内容：
1. 主力资金流向分析（大单净流入数据）
2. 外资态度分析（"香港中央结算"持股比例变化 + 是否进入沪深港通十大成交）
3. 基金持股分析（公募基金持股变化）
4. 融资融券数据分析（融资余额变化百分比）
5. 大宗交易记录分析（如有）
6. 股权质押风险评估
7. 筹码集中度判断

报告末尾附上两个Markdown表格：

表1：资金流向汇总
| 资金类型 | 近期变化 | 趋势 | 判断 |
|---------|-----------|------|------|
| 主力资金 | +/-X万元（近10日） | 流入/流出 | 看多/看空 |
| 外资态度 | 香港中央结算持股X%（较上期+/-Y%） | 增持/减持/稳定 | 看好/谨慎/中性 |
| 基金持股 | X只基金持有/占流通股Y% | 增持/减持/稳定 | 机构看好/谨慎/中性 |
| 融资余额 | +/-X% | 上升/下降 | 杠杆看多/去杠杆 |

表2：风险信号监测
| 风险类型 | 当前状态 | 风险等级 | 应对建议 |
|---------|---------|---------|---------|
| 质押风险 | 质押比例X% | 高/中/低 | - |
| 大宗减持 | 近30日X笔 | 高/中/低 | - |
| 杠杆风险 | 融资增速X% | 高/中/低 | - |
| 筹码分散 | 股东变化X% | 高/中/低 | - |

【数据缺失处理】
如果某些数据无法获取，请按以下方式处理：
1. **必需数据**（主力资金流向、股东人数）：如缺失，需明确说明，降低置信度
2. **外资态度数据**：从前十大股东中找"香港中央结算"；如该股东未出现在十大股东中，说明外资持股较少
3. **大宗交易/质押数据**：如无法获取，在风险表格中标注"待确认"
4. **龙虎榜数据**：非必需，如缺失可跳过该部分

信号冲突处理：
- 主力流入 + 外资减持（香港中央结算持股下降）：以主力资金为主，但需注明外资态度谨慎
- 融资增加 + 股东增加：可能是散户杠杆入场，提示追高风险
- 龙虎榜机构买入 + 股东人数增加：短期可能有机会，中期筹码分散需警惕

置信度评估（在报告末尾标注）：
- 高置信度：主力资金+前十大股东（含外资）+融资融券数据齐全
- 中置信度：仅有主力资金流向
- 低置信度：核心资金数据缺失"""
        elif toolkit.config["online_tools"]:
            tools = [toolkit.get_stock_news_openai]
            system_message = (
                "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. Try to look at all sources possible from social media to sentiment to news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + """ Make sure to append a Makrdown table at the end of the report to organize key points in the report, organized and easy to read."""
            )
        else:
            tools = [
                toolkit.get_reddit_stock_info,
            ]
            system_message = (
                "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. Try to look at all sources possible from social media to sentiment to news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + """ Make sure to append a Makrdown table at the end of the report to organize key points in the report, organized and easy to read."""
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The current company we want to analyze is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "sentiment_report": report,
        }

    return social_media_analyst_node
