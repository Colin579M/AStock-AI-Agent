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


def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # 根据市场类型选择工具
        if is_china_stock(ticker):
            # 中国A股使用 akshare 新闻工具 + Tushare 宏观数据
            tools = [
                toolkit.get_tushare_stock_basic,  # 首先获取股票基本信息（准确名称）
                toolkit.get_china_stock_news,     # akshare 个股新闻
                toolkit.get_china_market_news,    # akshare 市场新闻
                toolkit.get_tushare_pmi,          # Tushare PMI 采购经理指数
                toolkit.get_google_news,          # 备用，用于获取国际新闻
            ]
            system_message = """您是一位专业的中国财经新闻分析师，负责收集和分析与目标股票相关的新闻资讯和宏观经济数据。

【重要】数据获取顺序：
1. **首先调用 get_tushare_stock_basic** 获取股票基本信息，确认股票的准确名称
2. 调用 get_china_stock_news 获取个股相关新闻
3. 调用 get_china_market_news 获取市场整体新闻和财联社快讯
4. 调用 get_tushare_pmi 获取PMI采购经理指数（宏观经济先行指标）
5. 如需要，调用 get_google_news 获取补充的国际财经新闻

【股票代码格式】Tushare使用的格式：
- 上海股票：股票代码.SH（如 601899.SH）
- 深圳股票：股票代码.SZ（如 000001.SZ）

分析要点：
- **公司新闻**: 分析公司公告、业绩发布、重大事项等对股价的潜在影响
- **行业动态**: 关注所在行业的政策变化、竞争格局变化
- **宏观经济**:
  - PMI指数分析（>50表示扩张，<50表示收缩）
  - 制造业PMI vs 非制造业PMI
  - PMI趋势对行业的影响
- **市场情绪**: 从新闻角度判断市场情绪是乐观还是悲观
- **风险提示**: 识别新闻中的潜在风险信号

中国财经新闻特色：
- 关注政策导向（如产业政策、行业监管）
- 注意官方媒体（新华社、央视）的重要表态
- 财联社快讯的时效性和市场敏感度
- 龙头公司动态对板块的带动作用
- PMI数据对周期性行业的指导意义

请撰写详细的中文新闻分析报告，在报告标题中使用从 get_tushare_stock_basic 获取的准确股票名称，总结近期重要新闻及其对投资决策的影响，并在报告末尾附上Markdown表格总结关键新闻要点。"""
        elif toolkit.config["online_tools"]:
            tools = [toolkit.get_global_news_openai, toolkit.get_google_news]
            system_message = (
                "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Look at news from EODHD, and finnhub to be comprehensive. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + """ Make sure to append a Makrdown table at the end of the report to organize key points in the report, organized and easy to read."""
            )
        else:
            tools = [
                toolkit.get_finnhub_news,
                toolkit.get_reddit_news,
                toolkit.get_google_news,
            ]
            system_message = (
                "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Look at news from EODHD, and finnhub to be comprehensive. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
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
                    "For your reference, the current date is {current_date}. We are looking at the company {ticker}",
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
            "news_report": report,
        }

    return news_analyst_node
