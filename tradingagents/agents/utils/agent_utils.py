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
        使用Tushare获取中国A股财务指标，包括ROE、ROA、毛利率、净利率、资产负债率等150+个指标。
        这是最全面的财务分析数据源，涵盖盈利能力、偿债能力、成长能力等维度。
        Args:
            stock_code (str): 股票代码，如 601899（紫金矿业）
        Returns:
            str: 格式化的财务指标分析，按盈利能力、每股指标、偿债能力、增长率分类展示
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
        使用Tushare获取沪深港通资金流向（北向资金），包括沪股通、深股通每日净买入。
        北向资金是外资态度的重要风向标，对A股市场有重要影响。
        Returns:
            str: 格式化的北向资金流向数据，包含近10日流向及趋势分析
        """
        from tradingagents.dataflows.tushare_utils import get_hsgt_flow
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
