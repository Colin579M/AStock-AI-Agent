from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


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


def create_social_media_analyst(llm, toolkit):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # 根据市场类型选择工具
        if is_china_stock(ticker):
            # 中国A股使用 Tushare Pro 情绪和资金流向工具（高质量数据）
            tools = [
                toolkit.get_tushare_stock_basic,           # 首先获取股票基本信息（准确名称）
                toolkit.get_tushare_moneyflow,             # 资金流向（大/中/小单）
                toolkit.get_tushare_hsgt_flow,             # 北向资金流向
                toolkit.get_tushare_margin,                # 融资融券数据
                toolkit.get_tushare_top10_holders,         # 前十大股东
                toolkit.get_tushare_holder_number,         # 股东人数（筹码集中度）
                toolkit.get_tushare_top_list,              # 龙虎榜
                toolkit.get_tushare_sentiment_comprehensive,  # 综合情绪数据包
            ]
            system_message = """您是一位专业的中国A股市场情绪分析师，负责分析市场情绪和资金流向。

【重要】您必须使用 Tushare 系列工具获取数据，这些是最准确的数据源：
1. **首先调用 get_tushare_stock_basic** 获取股票基本信息，确认股票的准确名称
2. 调用 get_tushare_moneyflow 获取资金流向数据（大单/中单/小单/超大单）
3. 调用 get_tushare_hsgt_flow 获取北向资金流向（沪深港通）
4. 调用 get_tushare_margin 获取融资融券数据
5. 调用 get_tushare_top10_holders 获取前十大股东
6. 调用 get_tushare_holder_number 获取股东人数变化（筹码集中度）
7. 调用 get_tushare_top_list 获取龙虎榜数据
8. 或直接调用 get_tushare_sentiment_comprehensive 获取综合情绪数据包

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

情绪指标解读：
- 主力流入 + 北向流入 + 股东减少 = 强势看多信号
- 主力流出 + 散户接盘 + 股东增加 = 可能见顶信号
- 融资余额持续增加 = 杠杆资金看多

请撰写详细的中文情绪分析报告，在报告标题中使用从 get_tushare_stock_basic 获取的准确股票名称，重点分析资金流向和市场情绪对股价的潜在影响，并在报告末尾附上Markdown表格总结关键情绪指标。"""
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
