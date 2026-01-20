from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import functools
import pandas as pd
import os
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import tradingagents.dataflows.interface as interface
from tradingagents.default_config import DEFAULT_CONFIG
from langchain_core.messages import HumanMessage


def is_china_stock(ticker: str) -> bool:
    """
    判断是否为中国A股股票代码

    支持的代码格式:
    - 上海: 600xxx, 601xxx, 603xxx, 605xxx, 688xxx (科创板)
    - 深圳: 000xxx, 001xxx, 002xxx, 003xxx, 300xxx, 301xxx (创业板)
    - 北交所: 8xxxxx, 4xxxxx (暂不支持)

    Args:
        ticker: 股票代码，支持带后缀格式如 600036.SH
    Returns:
        bool: True 如果是中国A股代码
    """
    if not ticker:
        return False
    # 移除可能的后缀（如 .SS, .SZ, .SH）
    clean_ticker = ticker.split('.')[0].strip()
    # 判断是否为6位数字
    if clean_ticker.isdigit() and len(clean_ticker) == 6:
        # 深圳：000xxx, 001xxx (2021年后新增), 002xxx, 003xxx, 300xxx, 301xxx
        # 上海：600xxx, 601xxx, 603xxx, 605xxx, 688xxx
        prefix = clean_ticker[:3]
        valid_prefixes = ['000', '001', '002', '003', '300', '301', '600', '601', '603', '605', '688']
        if prefix in valid_prefixes:
            return True
    return False


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]
        
        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]
        
        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")
        
        return {"messages": removal_operations + [placeholder]}
    
    return delete_messages


class Toolkit:
    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)

    @staticmethod
    @tool
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve global news from Reddit within a specified time frame.
        Args:
            curr_date (str): Date you want to get news for in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the latest global news from Reddit in the specified time frame.
        """
        
        global_news_result = interface.get_reddit_global_news(curr_date, 7, 5)

        return global_news_result

    @staticmethod
    @tool
    def get_finnhub_news(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock from Finnhub within a date range
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing news about the company within the date range from start_date to end_date
        """

        end_date_str = end_date

        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        look_back_days = (end_date - start_date).days

        finnhub_news_result = interface.get_finnhub_news(
            ticker, end_date_str, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    @tool
    def get_reddit_stock_info(
        ticker: Annotated[
            str,
            "Ticker of a company. e.g. AAPL, TSM",
        ],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """
        Retrieve the latest news about a given stock from Reddit, given the current date.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): current date in yyyy-mm-dd format to get news for
        Returns:
            str: A formatted dataframe containing the latest news about the company on the given date
        """

        stock_news_results = interface.get_reddit_company_news(ticker, curr_date, 7, 5)

        return stock_news_results

    @staticmethod
    @tool
    def get_YFin_data(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_YFin_data_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data_online(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_stockstats_indicators_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, False
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_stockstats_indicators_report_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, True
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_finnhub_company_insider_sentiment(
        ticker: Annotated[str, "ticker symbol for the company"],
        curr_date: Annotated[
            str,
            "current date of you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider sentiment information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the sentiment in the past 30 days starting at curr_date
        """

        data_sentiment = interface.get_finnhub_company_insider_sentiment(
            ticker, curr_date, 30
        )

        return data_sentiment

    @staticmethod
    @tool
    def get_finnhub_company_insider_transactions(
        ticker: Annotated[str, "ticker symbol"],
        curr_date: Annotated[
            str,
            "current date you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider transaction information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's insider transactions/trading information in the past 30 days
        """

        data_trans = interface.get_finnhub_company_insider_transactions(
            ticker, curr_date, 30
        )

        return data_trans

    @staticmethod
    @tool
    def get_simfin_balance_sheet(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent balance sheet of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's most recent balance sheet
        """

        data_balance_sheet = interface.get_simfin_balance_sheet(ticker, freq, curr_date)

        return data_balance_sheet

    @staticmethod
    @tool
    def get_simfin_cashflow(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent cash flow statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent cash flow statement
        """

        data_cashflow = interface.get_simfin_cashflow(ticker, freq, curr_date)

        return data_cashflow

    @staticmethod
    @tool
    def get_simfin_income_stmt(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent income statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent income statement
        """

        data_income_stmt = interface.get_simfin_income_statements(
            ticker, freq, curr_date
        )

        return data_income_stmt

    @staticmethod
    @tool
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news from Google News based on a query and date range.
        Args:
            query (str): Query to search with
            curr_date (str): Current date in yyyy-mm-dd format
            look_back_days (int): How many days to look back
        Returns:
            str: A formatted string containing the latest news from Google News based on the query and date range.
        """

        google_news_results = interface.get_google_news(query, curr_date, 7)

        return google_news_results

    @staticmethod
    @tool
    def get_stock_news_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news about the company on the given date.
        """

        openai_news_results = interface.get_stock_news_openai(ticker, curr_date)

        return openai_news_results

    @staticmethod
    @tool
    def get_global_news_openai(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest macroeconomics news on a given date using OpenAI's macroeconomics news API.
        Args:
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest macroeconomic news on the given date.
        """

        openai_news_results = interface.get_global_news_openai(curr_date)

        return openai_news_results

    @staticmethod
    @tool
    def get_fundamentals_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest fundamental information about a given stock on a given date by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest fundamental information about the company on the given date.
        """

        openai_fundamentals_results = interface.get_fundamentals_openai(
            ticker, curr_date
        )

        return openai_fundamentals_results

    @staticmethod
    @tool
    def get_china_stock_data(
        stock_code: Annotated[str, "股票代码，如 000001, 600519, 601899"],
        start_date: Annotated[str, "开始日期 yyyy-mm-dd 格式"],
        end_date: Annotated[str, "结束日期 yyyy-mm-dd 格式"],
    ) -> str:
        """
        获取中国A股股票数据，包括实时行情、历史数据和技术指标。
        通过通达信API获取数据，支持深圳和上海市场的股票。
        Args:
            stock_code (str): 股票代码，如 000001（平安银行）, 600519（贵州茅台）, 601899（紫金矿业）
            start_date (str): 开始日期，格式为 yyyy-mm-dd
            end_date (str): 结束日期，格式为 yyyy-mm-dd
        Returns:
            str: 格式化的股票数据报告，包含实时行情、历史数据和技术指标分析
        """
        from tradingagents.dataflows.tdx_utils import get_china_stock_data
        return get_china_stock_data(stock_code, start_date, end_date)

    @staticmethod
    @tool
    def get_china_market_overview() -> str:
        """
        获取中国股市概览，包括上证指数、深证成指、创业板指等主要指数的实时数据。
        Returns:
            str: 格式化的市场概览报告，包含主要指数的当前点位、涨跌幅和成交量
        """
        from tradingagents.dataflows.tdx_utils import get_china_market_overview
        return get_china_market_overview()

    # ========================================================================
    # 中国A股基本面数据工具 (akshare)
    # ========================================================================

    @staticmethod
    @tool
    def get_china_financial_report(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
        report_type: Annotated[str, "报表类型: balance(资产负债表), income(利润表), cashflow(现金流量表), all(全部)"] = "all",
    ) -> str:
        """
        获取中国A股财务报表数据，包括资产负债表、利润表、现金流量表。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）, 000001（平安银行）
            report_type (str): 报表类型 - balance/income/cashflow/all
        Returns:
            str: 格式化的财务报表数据，包含最近4个季度的关键财务指标
        """
        from tradingagents.dataflows.akshare_utils import get_financial_report
        return get_financial_report(stock_code, report_type)

    @staticmethod
    @tool
    def get_china_stock_indicators(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        获取中国A股核心财务指标，包括PE、PB、ROE、毛利率、净利率、市值等估值和盈利指标。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）, 000001（平安银行）
        Returns:
            str: 格式化的核心指标数据，包含估值指标和财务分析指标
        """
        from tradingagents.dataflows.akshare_utils import get_stock_indicators
        return get_stock_indicators(stock_code)

    @staticmethod
    @tool
    def get_china_earnings_forecast(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        获取中国A股业绩预告和业绩报表数据。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）, 000001（平安银行）
        Returns:
            str: 格式化的业绩预告和报表数据，包含预期收益、增长率等
        """
        from tradingagents.dataflows.akshare_utils import get_earnings_forecast
        return get_earnings_forecast(stock_code)

    # ========================================================================
    # 中国A股新闻数据工具 (akshare)
    # ========================================================================

    @staticmethod
    @tool
    def get_china_stock_news(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
        curr_date: Annotated[str, "当前日期 yyyy-mm-dd 格式"],
    ) -> str:
        """
        获取中国A股个股相关新闻，来自东方财富等财经网站。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 格式化的个股新闻列表，包含新闻标题、内容摘要和发布时间
        """
        from tradingagents.dataflows.akshare_utils import get_china_stock_news
        return get_china_stock_news(stock_code, curr_date)

    @staticmethod
    @tool
    def get_china_market_news(
        curr_date: Annotated[str, "当前日期 yyyy-mm-dd 格式"],
    ) -> str:
        """
        获取中国财经市场新闻，包括财联社快讯、央视新闻联播经济要点等。
        Args:
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 格式化的市场新闻汇总，包含最新财经快讯和重要经济新闻
        """
        from tradingagents.dataflows.akshare_utils import get_china_market_news
        return get_china_market_news(curr_date)

    # ========================================================================
    # 中国A股情绪数据工具 (akshare)
    # ========================================================================

    @staticmethod
    @tool
    def get_china_stock_sentiment(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        获取中国A股市场情绪数据，包括千股千评、人气排名、热门关键词等。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的情绪分析数据，包含综合评价、热度排名和市场关注度
        """
        from tradingagents.dataflows.akshare_utils import get_china_stock_sentiment
        return get_china_stock_sentiment(stock_code)

    @staticmethod
    @tool
    def get_china_money_flow(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        获取中国A股资金流向数据，包括主力资金、散户资金、北向资金流向。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的资金流向分析，包含近期资金流入流出、北向资金持仓情况
        """
        from tradingagents.dataflows.akshare_utils import get_china_money_flow
        return get_china_money_flow(stock_code)

    # ========================================================================
    # 中国A股 Tushare Pro 数据工具（高质量数据源）
    # ========================================================================

    @staticmethod
    @tool
    def get_tushare_financial_statements(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取中国A股完整财务报表，包括利润表、资产负债表、现金流量表。
        提供比akshare更完整的财务数据（60+字段利润表、114字段资产负债表）。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）, 000001（平安银行）
        Returns:
            str: 格式化的财务三表数据，包含最近4个季度的关键财务指标
        """
        from tradingagents.dataflows.tushare_utils import get_financial_statements
        return get_financial_statements(stock_code)

    @staticmethod
    @tool
    def get_tushare_financial_indicators(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取中国A股财务指标（5年历史+近4季详细），支持周期股估值分析。

        返回内容：
        1. **历史指标摘要**（5年/20季度）：EPS/ROE/毛利率的平均值、最高、最低、当前值及周期位置判断
        2. **近4季详细数据**：盈利能力、每股指标、偿债能力、增长率

        周期位置判断：低位(<25%)/偏低(25-50%)/偏高(50-75%)/高位(>75%)

        Args:
            stock_code (str): 股票代码，如 601088（中国神华）、601899（紫金矿业）
        Returns:
            str: 格式化的财务指标分析，含历史摘要（周期分析用）和近4季详细数据
        """
        from tradingagents.dataflows.tushare_utils import get_financial_indicators
        return get_financial_indicators(stock_code)

    @staticmethod
    @tool
    def get_tushare_daily_basic(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
        trade_date: Annotated[str, "交易日期 YYYYMMDD 格式，可选"] = "",
    ) -> str:
        """
        使用Tushare获取每日估值指标，包括PE(TTM)、PB、PS、总市值、流通市值、换手率、量比。
        提供更准确的实时估值数据，支持历史估值对比分析。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
            trade_date (str): 交易日期 YYYYMMDD 格式，留空获取最近数据
        Returns:
            str: 格式化的估值指标数据，包含最近10个交易日的估值变化
        """
        from tradingagents.dataflows.tushare_utils import get_daily_basic
        return get_daily_basic(stock_code, trade_date if trade_date else None)

    @staticmethod
    @tool
    def get_tushare_forecast(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取业绩预告，包括预告类型、业绩变动幅度、预计净利润、变动原因。
        提供最新的业绩预告和业绩快报数据，帮助判断公司未来业绩预期。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的业绩预告数据，包含最近5条业绩预告信息
        """
        from tradingagents.dataflows.tushare_utils import get_forecast
        return get_forecast(stock_code)

    @staticmethod
    @tool
    def get_tushare_top10_holders(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取前十大股东数据，包括股东名称、持股数量、持股比例、股东类型。
        这是分析机构持仓和大股东动向的重要数据源。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的前十大股东列表及合计持股比例
        """
        from tradingagents.dataflows.tushare_utils import get_top10_holders
        return get_top10_holders(stock_code)

    @staticmethod
    @tool
    def get_tushare_holder_number(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取股东人数变化趋势，反映筹码集中度。
        股东人数减少通常意味着主力吸筹，股东人数增加可能意味着主力派发。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的股东人数变化数据及趋势分析
        """
        from tradingagents.dataflows.tushare_utils import get_holder_number
        return get_holder_number(stock_code)

    @staticmethod
    @tool
    def get_tushare_moneyflow(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取个股资金流向，按大单/中单/小单分类统计净流入流出。
        提供更精细的资金分类（5万/20万/100万分界），准确反映主力资金动向。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的资金流向数据，包含近10日每日明细及汇总
        """
        from tradingagents.dataflows.tushare_utils import get_moneyflow
        return get_moneyflow(stock_code)

    @staticmethod
    @tool
    def get_tushare_hsgt_flow() -> str:
        """
        获取北向资金持股排行数据。

        ⚠️ **重要**：北向资金整体流向（每日净流入/流出）已于2024年8月停止披露。
        本工具仅返回仍可用的持股排行数据（但数据也可能过时）。

        **推荐外资态度分析方案**：使用 get_tushare_top10_holders(stock_code)
        查看前十大股东中"香港中央结算"的持股比例（季度数据，仍在更新）。

        Returns:
            str: 北向资金持股排行（⚠️ 数据可能已过时，请核对日期）
        """
        from tradingagents.dataflows.akshare_utils import get_hsgt_flow
        return get_hsgt_flow()

    @staticmethod
    @tool
    def get_tushare_margin(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取融资融券数据，包括融资余额、融资买入、融券余额、融券卖出。
        融资融券数据反映杠杆资金的多空态度，是重要的市场情绪指标。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的融资融券数据及趋势分析
        """
        from tradingagents.dataflows.tushare_utils import get_margin_data
        return get_margin_data(stock_code)

    @staticmethod
    @tool
    def get_tushare_pmi() -> str:
        """
        使用Tushare获取PMI采购经理指数，包括制造业PMI、新订单、生产、从业人员等指标。
        PMI是宏观经济的先行指标，50以上表示扩张，50以下表示收缩。
        Returns:
            str: 格式化的PMI数据及宏观经济分析
        """
        from tradingagents.dataflows.tushare_utils import get_pmi
        return get_pmi()

    @staticmethod
    @tool
    def get_tushare_cctv_news(
        date: Annotated[str, "日期，格式 YYYYMMDD 或 YYYY-MM-DD，默认今天"] = None,
    ) -> str:
        """
        使用Tushare获取新闻联播文字稿，筛选经济相关内容。
        新闻联播是重要的政策风向标，关注经济、金融、产业相关内容有助于把握政策方向。
        Args:
            date (str): 日期，格式 YYYYMMDD 或 YYYY-MM-DD，默认今天
        Returns:
            str: 格式化的新闻联播经济要点
        """
        from tradingagents.dataflows.tushare_utils import get_cctv_news
        if date:
            date = date.replace("-", "")
        return get_cctv_news(date)

    @staticmethod
    @tool
    def get_tushare_market_news(
        date: Annotated[str, "日期，格式 YYYYMMDD 或 YYYY-MM-DD，默认今天"] = None,
    ) -> str:
        """
        使用Tushare获取中国财经市场新闻，整合新闻联播和重大新闻。
        提供宏观经济和市场层面的新闻信息，帮助理解市场环境。
        Args:
            date (str): 日期，格式 YYYYMMDD 或 YYYY-MM-DD，默认今天
        Returns:
            str: 格式化的市场新闻汇总
        """
        from tradingagents.dataflows.tushare_utils import get_china_market_news_tushare
        return get_china_market_news_tushare(date)

    @staticmethod
    @tool
    def get_tushare_dividend(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取分红送股历史，包括每股分红、送股、转增、除权日等信息。
        历史分红数据可用于计算股息率，评估公司价值投资吸引力。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的分红历史数据
        """
        from tradingagents.dataflows.tushare_utils import get_dividend
        return get_dividend(stock_code)

    @staticmethod
    @tool
    def get_tushare_top_list(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取龙虎榜数据，包括上榜原因、买入卖出金额、净买入等信息。
        龙虎榜反映机构和游资的交易动向，是短线资金博弈的重要参考。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的龙虎榜数据
        """
        from tradingagents.dataflows.tushare_utils import get_top_list
        return get_top_list(stock_code)

    @staticmethod
    @tool
    def get_tushare_stock_basic(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取股票基本信息，包括代码、名称、全称、行业、地区、上市日期等。
        这是获取股票准确名称和基本属性的可靠数据源。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的股票基本信息
        """
        from tradingagents.dataflows.tushare_utils import get_stock_basic_info
        return get_stock_basic_info(stock_code)

    @staticmethod
    @tool
    def get_tushare_fundamentals_comprehensive(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取A股基本面综合数据包，一次性返回财务报表、财务指标、业绩预告、分红历史。
        这是进行基本面分析的一站式数据源，适合全面评估公司价值。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的基本面综合分析报告
        """
        from tradingagents.dataflows.tushare_utils import get_china_stock_fundamentals
        return get_china_stock_fundamentals(stock_code)

    @staticmethod
    @tool
    def get_tushare_sentiment_comprehensive(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取A股市场情绪综合数据包，一次性返回资金流向、北向资金、融资融券、股东数据。
        这是进行情绪分析的一站式数据源，适合判断市场资金面和投资者情绪。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的市场情绪综合分析报告
        """
        from tradingagents.dataflows.tushare_utils import get_china_stock_sentiment
        return get_china_stock_sentiment(stock_code)

    # ========================================================================
    # 中国A股 Tushare Pro 扩展数据工具（Phase 1.2 新增）
    # ========================================================================

    # ============= 已废弃工具说明 =============
    # get_tushare_hk_hold() 工具已移除
    # 废弃原因：港交所自2024年8月20日起停止披露北向资金每日数据
    # hk_hold API 目前仅返回季度数据，无法用于短期交易分析
    # 替代方案：使用 get_tushare_top10_holders() 查看"香港中央结算"持股比例
    # ==========================================

    @staticmethod
    @tool
    def get_tushare_hsgt_top10(
        trade_date: Annotated[str, "交易日期 YYYYMMDD 或 YYYY-MM-DD 格式，可选"] = "",
    ) -> str:
        """
        使用AKShare获取北向资金十大持股股，查看北向资金重点持有的股票。
        用于判断某只股票是否进入外资关注的热门标的。
        Args:
            trade_date (str): 交易日期 YYYYMMDD 或 YYYY-MM-DD 格式，留空获取最近数据
        Returns:
            str: 格式化的北向资金十大持股列表（按持股市值排序）
        """
        from tradingagents.dataflows.akshare_utils import get_hsgt_top10
        return get_hsgt_top10(trade_date if trade_date else None)

    @staticmethod
    @tool
    def get_tushare_hsgt_individual(
        stock_code: Annotated[str, "股票代码，如 600036, 000001"],
    ) -> str:
        """
        获取个股北向资金持股历史（⚠️ 数据已停更，仅返回历史数据）

        ⚠️ **警告**：此接口数据已于2024年8月停更，返回的是历史数据。

        **推荐替代方案**：使用 get_tushare_top10_holders(stock_code) 查看
        前十大股东中"香港中央结算"的持股比例（季度数据，仍在更新）。

        Args:
            stock_code (str): 股票代码，如 600036（招商银行）
        Returns:
            str: 格式化的个股北向资金持股历史数据（⚠️ 截止2024-08-16）
        """
        from tradingagents.dataflows.akshare_utils import get_hsgt_individual
        return get_hsgt_individual(stock_code)

    @staticmethod
    @tool
    def get_tushare_block_trade(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
        days: Annotated[int, "获取天数，默认30天"] = 30,
    ) -> str:
        """
        使用Tushare获取大宗交易数据，包括成交价、成交量、买卖营业部。
        大宗交易频繁且折价较大可能是减持信号，需关注交易背后的动机。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
            days (int): 获取天数，默认30天
        Returns:
            str: 格式化的大宗交易记录及风险分析
        """
        from tradingagents.dataflows.tushare_utils import get_block_trade
        return get_block_trade(stock_code, days)

    @staticmethod
    @tool
    def get_tushare_pledge_stat(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取股权质押统计，包括质押比例、质押次数、质押股份。
        质押比例超过30%需重点关注，超过50%存在平仓风险。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的股权质押数据及风险评估
        """
        from tradingagents.dataflows.tushare_utils import get_pledge_stat
        return get_pledge_stat(stock_code)

    @staticmethod
    @tool
    def get_tushare_share_float(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取限售解禁日历，包括未来6个月的解禁时点、解禁数量、解禁股东。
        大规模解禁可能对股价形成压力，需提前关注解禁时点和解禁股东成本。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的解禁日历及风险提示
        """
        from tradingagents.dataflows.tushare_utils import get_share_float
        return get_share_float(stock_code)

    @staticmethod
    @tool
    def get_tushare_index_daily(
        index_code: Annotated[str, "指数代码，如 000300.SH（沪深300）, 399318.SZ（国证有色）"],
        days: Annotated[int, "获取天数，默认60天"] = 60,
    ) -> str:
        """
        使用Tushare获取指数日线行情，用于分析板块走势和个股相对强弱。
        常用指数: 000300.SH沪深300, 399006.SZ创业板指, 399318.SZ国证有色, 000001.SH上证指数
        Args:
            index_code (str): 指数代码，如 399318.SZ（国证有色）
            days (int): 获取天数，默认60天
        Returns:
            str: 格式化的指数行情数据及趋势分析
        """
        from tradingagents.dataflows.tushare_utils import get_index_daily
        return get_index_daily(index_code, days)

    @staticmethod
    @tool
    def get_tushare_index_member(
        index_code: Annotated[str, "指数代码，默认 399318.SZ（国证有色）"] = "399318.SZ",
    ) -> str:
        """
        使用Tushare获取指数成分股列表，用于板块联动分析和同行业对比。
        常用指数: 399318.SZ国证有色, 000300.SH沪深300, 399006.SZ创业板指
        Args:
            index_code (str): 指数代码，默认为国证有色 399318.SZ
        Returns:
            str: 格式化的指数成分股列表
        """
        from tradingagents.dataflows.tushare_utils import get_index_member
        return get_index_member(index_code)

    @staticmethod
    @tool
    def get_sector_benchmark_data(
        stock_code: Annotated[str, "股票代码，如 601899, 000001, 300750"],
        days: Annotated[int, "获取天数，默认60天"] = 60,
    ) -> str:
        """
        智能获取个股所属行业的板块指数数据（傻瓜化工具）。
        只需传入股票代码，自动匹配行业指数并返回板块走势和相对强弱分析。

        示例:
        - 601899（紫金矿业）→ 自动匹配国证有色(399318.SZ)
        - 600519（贵州茅台）→ 自动匹配中证酒(399987.SZ)
        - 600036（招商银行）→ 自动匹配中证银行(399986.SZ)

        Args:
            stock_code (str): 股票代码
            days (int): 获取天数，默认60天
        Returns:
            str: 包含行业名称、对标指数、指数走势、相对强弱分析的完整报告
        """
        from tradingagents.dataflows.tushare_utils import get_sector_benchmark_data
        return get_sector_benchmark_data(stock_code, days)

    @staticmethod
    @tool
    def get_tushare_stk_surv(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取机构调研数据，包括调研日期、参与机构数量、调研形式。
        调研密度反映机构关注度，频繁调研通常意味着机构对公司有浓厚兴趣。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的机构调研记录及关注度分析
        """
        from tradingagents.dataflows.tushare_utils import get_stk_surv
        return get_stk_surv(stock_code)

    @staticmethod
    @tool
    def get_tushare_report_rc(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
        days: Annotated[int, "获取天数，默认30天"] = 30,
    ) -> str:
        """
        使用Tushare获取券商研报数据，包括研报标题、评级、目标价、发布机构。
        券商研报反映机构一致预期，目标价可作为估值参考。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
            days (int): 获取天数，默认30天
        Returns:
            str: 格式化的券商研报数据及评级统计
        """
        from tradingagents.dataflows.tushare_utils import get_report_rc
        return get_report_rc(stock_code, days)

    @staticmethod
    @tool
    def get_tushare_fut_daily(
        fut_code: Annotated[str, "期货代码，如 CU.SHF（沪铜）, AU.SHF（沪金）"],
        days: Annotated[int, "获取天数，默认60天"] = 60,
    ) -> str:
        """
        使用Tushare获取期货日线数据，用于分析商品价格走势对周期股的影响。
        常用期货: CU沪铜, AU沪金, AG沪银, AL沪铝, ZN沪锌, NI沪镍
        Args:
            fut_code (str): 期货代码，如 CU.SHF（沪铜）, AU.SHF（沪金）
            days (int): 获取天数，默认60天
        Returns:
            str: 格式化的期货行情数据及趋势分析
        """
        from tradingagents.dataflows.tushare_utils import get_fut_daily
        return get_fut_daily(fut_code, days)

    # ========================================================================
    # 中国A股 Tushare Pro 综合数据工具（Phase 1.2 新增）
    # ========================================================================

    @staticmethod
    @tool
    def get_tushare_capital_deep(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取深度资金分析数据包，一次性返回北向持股、大宗交易、股权质押、解禁日历。
        这是进行资金面深度分析的一站式数据源，适合评估资金风险和潜在供给压力。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的深度资金分析报告
        """
        from tradingagents.dataflows.tushare_utils import get_china_stock_capital_deep
        return get_china_stock_capital_deep(stock_code)

    @staticmethod
    @tool
    def get_tushare_institution(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取机构观点数据包，一次性返回机构调研和券商研报数据。
        这是了解机构对公司看法的一站式数据源，适合判断机构共识和目标价预期。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的机构观点综合报告
        """
        from tradingagents.dataflows.tushare_utils import get_china_stock_institution
        return get_china_stock_institution(stock_code)

    # ========================================================================
    # 中国A股 Tushare Pro 扩展数据工具（2024-01 新增）
    # ========================================================================

    @staticmethod
    @tool
    def get_tushare_repurchase(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取股票回购数据。
        回购是管理层认为股价被低估的重要信号，对判断公司价值有重要参考。
        包含回购计划、进度、金额、目的等信息。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的股票回购分析报告
        """
        from tradingagents.dataflows.tushare_utils import get_repurchase
        return get_repurchase(stock_code)

    @staticmethod
    @tool
    def get_tushare_fund_shares(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取基金持股数据。
        包括公募基金、社保基金、QFII等机构持股情况，以及持仓变动。
        用于分析机构投资者的持仓态度和变化趋势。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的基金持股分析报告
        """
        from tradingagents.dataflows.tushare_utils import get_fund_shares
        return get_fund_shares(stock_code)

    @staticmethod
    @tool
    def get_tushare_adj_factor(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
        start_date: Annotated[str, "开始日期 YYYYMMDD，可选"] = None,
        end_date: Annotated[str, "结束日期 YYYYMMDD，可选"] = None,
    ) -> str:
        """
        使用Tushare获取复权因子数据。
        复权因子用于计算除权除息后的真实价格涨跌幅，识别分红、配股、送股事件。
        对于长期趋势分析和回测非常重要。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
            start_date (str): 开始日期，格式 YYYYMMDD
            end_date (str): 结束日期，格式 YYYYMMDD
        Returns:
            str: 格式化的复权因子分析报告
        """
        from tradingagents.dataflows.tushare_utils import get_adj_factor
        return get_adj_factor(stock_code, start_date, end_date)

    @staticmethod
    @tool
    def get_tushare_concept(
        stock_code: Annotated[str, "股票代码，如 601899, 000001"],
    ) -> str:
        """
        使用Tushare获取股票所属概念板块。
        了解股票所属的热点概念，判断板块联动效应和炒作机会。
        对于分析行业/板块动态和资金流向非常有用。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的概念板块分析报告
        """
        from tradingagents.dataflows.tushare_utils import get_concept
        return get_concept(stock_code)

    @staticmethod
    @tool
    def get_industry_tam(
        industry: Annotated[str, "行业名称，如 '医疗服务', '银行', '有色金属', '新能源'"],
        stock_code: Annotated[str, "股票代码（可选），用于辅助确定行业归属"] = "",
    ) -> str:
        """
        获取行业TAM（Total Addressable Market）和市场格局数据。

        用于成长股终局思维估值，返回：
        - 行业市场规模（TAM）估算
        - 行业增速区间和渗透率
        - 行业龙头和竞争格局
        - 推荐估值方法
        - 多头策略适用性（成长股/价值股/周期股）

        采用三级降级策略：
        1. Level 1: 精确TAM数据（如有行业研报）
        2. Level 2: Top5企业营收估算（使用Tushare数据）
        3. Level 3: 行业常数词典（兜底方案）

        Args:
            industry (str): 行业名称，支持：医疗服务、银行、保险、券商、有色金属、煤炭、钢铁、化工、
                           白酒、食品饮料、家电、新能源、半导体、互联网、电力、燃气、房地产、建筑等
            stock_code (str): 股票代码（可选）

        Returns:
            str: 格式化的行业TAM分析报告，包含市场规模、竞争格局、多头策略建议
        """
        from tradingagents.dataflows.tushare_utils import get_industry_tam_data
        return get_industry_tam_data(industry, stock_code if stock_code else None)

    # ========================================================================
    # 概念关联度验证工具（2026-01 新增）
    # ========================================================================

    @staticmethod
    @tool
    def get_investor_qa(
        stock_code: Annotated[str, "股票代码，如 002565, 601899"],
        keyword: Annotated[str, "搜索关键词，如 '航天', '人工智能'"] = "",
    ) -> str:
        """
        获取互动易/e互动投资者问答数据。
        深交所股票(0/3开头)使用互动易，上交所股票(6开头)使用e互动。
        用于追溯概念炒作起点和验证公司对特定业务的官方回应。

        Args:
            stock_code (str): 股票代码，如 002565（顺灏股份）
            keyword (str): 搜索关键词，如 '航天', '卫星'

        Returns:
            str: 格式化的投资者问答列表
        """
        from tradingagents.dataflows.concept_validator_utils import get_investor_qa
        return get_investor_qa(stock_code, keyword)

    @staticmethod
    @tool
    def get_announcement_search(
        stock_code: Annotated[str, "股票代码，如 002565, 601899"],
        keyword: Annotated[str, "搜索关键词，如 '子公司', '战略合作'"] = "",
        days: Annotated[int, "查询天数，默认365天"] = 365,
    ) -> str:
        """
        搜索公司公告（巨潮资讯），查找业务拓展、战略合作等关键信息。
        用于验证概念是否有公告依据，追溯业务变化时点。

        Args:
            stock_code (str): 股票代码
            keyword (str): 搜索关键词（如 '航天', '子公司', '战略合作'）
            days (int): 查询天数，默认365天

        Returns:
            str: 格式化的公告列表
        """
        from tradingagents.dataflows.concept_validator_utils import get_announcement_search
        return get_announcement_search(stock_code, keyword, days)

    @staticmethod
    @tool
    def get_concept_validation(
        stock_code: Annotated[str, "股票代码，如 002565, 601899"],
        target_concept: Annotated[str, "目标概念，如 '商业航天', '人工智能', '低空经济'"],
    ) -> str:
        """
        概念关联度验证工具 - 综合分析股票与特定概念的关联程度。

        数据来源：
        1. 官方概念板块（Tushare）
        2. 互动易/e互动投资者问答
        3. 公司公告搜索

        输出：
        - 关联度评分（0-100）
        - 关联等级：有实质业务(50-100) / 有公告提及(20-49) / 纯市场联想(0-19)
        - 证据链详情

        用于回答"这只股票为什么蹭XX概念"类问题。

        Args:
            stock_code (str): 股票代码，如 002565（顺灏股份）
            target_concept (str): 目标概念名称，如 '商业航天'

        Returns:
            str: 概念关联度验证报告
        """
        from tradingagents.dataflows.concept_validator_utils import get_concept_validation_report
        return get_concept_validation_report(stock_code, target_concept)
