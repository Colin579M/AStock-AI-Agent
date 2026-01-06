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


def create_fundamentals_analyst(llm, toolkit):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # 根据市场类型选择工具
        if is_china_stock(ticker):
            # 中国A股使用 Tushare Pro 基本面工具（高质量数据）
            tools = [
                toolkit.get_tushare_stock_basic,           # 首先获取股票基本信息（准确名称）
                toolkit.get_tushare_financial_statements,  # 财务三表
                toolkit.get_tushare_financial_indicators,  # 150+财务指标
                toolkit.get_tushare_daily_basic,           # 每日估值指标
                toolkit.get_tushare_forecast,              # 业绩预告
                toolkit.get_tushare_dividend,              # 分红历史
                toolkit.get_tushare_fundamentals_comprehensive,  # 综合数据包
            ]
            system_message = """您是一位专业的中国A股基本面分析师，负责深入分析上市公司的财务状况和投资价值。

【重要】您必须使用 Tushare 系列工具获取数据，这些是最准确的数据源：
1. **首先调用 get_tushare_stock_basic** 获取股票基本信息，确认股票的准确名称
2. 调用 get_tushare_financial_statements 获取财务三表（利润表、资产负债表、现金流量表）
3. 调用 get_tushare_financial_indicators 获取150+财务指标（ROE/ROA/毛利率/净利率等）
4. 调用 get_tushare_daily_basic 获取最新估值数据（PE/PB/PS/市值/换手率）
5. 调用 get_tushare_forecast 获取业绩预告信息
6. 调用 get_tushare_dividend 获取分红历史
7. 或直接调用 get_tushare_fundamentals_comprehensive 获取综合数据包

【股票代码格式】Tushare使用的格式：
- 上海股票：股票代码.SH（如 601899.SH）
- 深圳股票：股票代码.SZ（如 000001.SZ）

分析要点：
- **盈利能力分析**: 分析ROE、毛利率、净利率的趋势和行业对比
- **估值水平评估**: 分析PE、PB是否处于合理区间，与历史估值对比
- **成长性分析**: 分析营收增长率、净利润增长率，评估增长质量
- **财务健康度**: 分析资产负债率、流动比率、速动比率，评估偿债能力
- **现金流质量**: 分析经营性现金流是否健康，是否能覆盖投资需求
- **业绩预期**: 分析业绩预告信息，评估未来增长预期

中国A股特色考虑：
- 季报披露时间节点（4月、8月、10月）
- 年报预约披露时间
- 商誉减值风险
- 大股东质押比例
- 限售股解禁压力

请撰写详细的中文基本面分析报告，在报告标题中使用从 get_tushare_stock_basic 获取的准确股票名称，并在报告末尾附上Markdown表格总结关键财务指标和投资要点。"""
        elif toolkit.config["online_tools"]:
            tools = [toolkit.get_fundamentals_openai]
            system_message = (
                "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, company financial history, insider sentiment and insider transactions to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            )
        else:
            tools = [
                toolkit.get_finnhub_company_insider_sentiment,
                toolkit.get_finnhub_company_insider_transactions,
                toolkit.get_simfin_balance_sheet,
                toolkit.get_simfin_cashflow,
                toolkit.get_simfin_income_stmt,
            ]
            system_message = (
                "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, company financial history, insider sentiment and insider transactions to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
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
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
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
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
