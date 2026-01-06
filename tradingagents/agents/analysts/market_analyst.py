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
    # 中国A股代码特征：6位纯数字
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


def create_market_analyst(llm, toolkit):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # 判断市场类型并选择相应的工具
        if is_china_stock(ticker):
            # 中国A股使用通达信API + Tushare估值数据
            tools = [
                toolkit.get_tushare_stock_basic,   # 首先获取股票基本信息（准确名称）
                toolkit.get_china_stock_data,      # 通达信实时行情和技术指标
                toolkit.get_china_market_overview, # 市场概览
                toolkit.get_tushare_daily_basic,   # Tushare每日估值指标（PE/PB/换手率）
            ]
        elif toolkit.config["online_tools"]:
            # 美股/其他市场使用Yahoo Finance在线工具
            tools = [
                toolkit.get_YFin_data_online,
                toolkit.get_stockstats_indicators_report_online,
            ]
        else:
            # 离线模式使用缓存数据
            tools = [
                toolkit.get_YFin_data,
                toolkit.get_stockstats_indicators_report,
            ]

        # 根据市场类型选择合适的系统提示词
        if is_china_stock(ticker):
            system_message = """您是一位专业的中国A股市场分析师，负责分析股票的技术面和估值水平。

【重要】数据获取顺序：
1. **首先调用 get_tushare_stock_basic** 获取股票基本信息，确认股票的准确名称
2. 调用 get_china_stock_data 获取股票的实时行情、历史数据和技术指标（通达信API）
3. 调用 get_china_market_overview 了解整体市场环境
4. 调用 get_tushare_daily_basic 获取每日估值指标（PE/PB/市值/换手率）

【股票代码格式】
- 通达信工具：直接使用6位代码（如 601899）
- Tushare工具：上海股票用.SH后缀（如 601899.SH），深圳股票用.SZ后缀（如 000001.SZ）

分析要点：
- **技术面分析**: 分析MA均线系统、MACD、RSI、布林带等技术指标
- **趋势判断**: 判断当前股票处于上升趋势、下降趋势还是震荡整理
- **支撑与压力**: 识别关键的支撑位和压力位
- **成交量分析**: 分析量价关系，判断资金流向
- **估值分析**:
  - PE（市盈率）与历史对比
  - PB（市净率）与行业对比
  - 换手率判断交易活跃度
  - 市值规模评估
- **市场情绪**: 结合大盘走势分析个股的相对强弱

中国A股市场特色考虑：
- 涨跌停板限制（主板10%，创业板/科创板20%）
- T+1交易制度
- 融资融券对股价的影响
- 北向资金的动向

请撰写详细的中文分析报告，在报告标题中使用从 get_tushare_stock_basic 获取的准确股票名称，并在报告末尾附上Markdown表格总结关键发现。"""
        else:
            system_message = (
                """You are a trading assistant tasked with analyzing financial markets. Your role is to select the **most relevant indicators** for a given market condition or trading strategy from the following list. The goal is to choose up to **8 indicators** that provide complementary insights without redundancy. Categories and each category's indicators are:

Moving Averages:
- close_50_sma: 50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance. Tips: It lags price; combine with faster indicators for timely signals.
- close_200_sma: 200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups. Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries.
- close_10_ema: 10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points. Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals.

MACD Related:
- macd: MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes. Tips: Confirm with other indicators in low-volatility or sideways markets.
- macds: MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades. Tips: Should be part of a broader strategy to avoid false positives.
- macdh: MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength and spot divergence early. Tips: Can be volatile; complement with additional filters in fast-moving markets.

Momentum Indicators:
- rsi: RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis.

Volatility Indicators:
- boll: Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. Usage: Acts as a dynamic benchmark for price movement. Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals.
- boll_ub: Bollinger Upper Band: Typically 2 standard deviations above the middle line. Usage: Signals potential overbought conditions and breakout zones. Tips: Confirm signals with other tools; prices may ride the band in strong trends.
- boll_lb: Bollinger Lower Band: Typically 2 standard deviations below the middle line. Usage: Indicates potential oversold conditions. Tips: Use additional analysis to avoid false reversal signals.
- atr: ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes based on current market volatility. Tips: It's a reactive measure, so use it as part of a broader risk management strategy.

Volume-Based Indicators:
- vwma: VWMA: A moving average weighted by volume. Usage: Confirm trends by integrating price action with volume data. Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses.

- Select indicators that provide diverse and complementary information. Avoid redundancy (e.g., do not select both rsi and stochrsi). Also briefly explain why they are suitable for the given market context. When you tool call, please use the exact name of the indicators provided above as they are defined parameters, otherwise your call will fail. Please make sure to call get_YFin_data first to retrieve the CSV that is needed to generate indicators. Write a very detailed and nuanced report of the trends you observe. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."""
                + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
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
            "market_report": report,
        }

    return market_analyst_node
