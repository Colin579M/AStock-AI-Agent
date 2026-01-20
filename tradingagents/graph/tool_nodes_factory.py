"""
Tool Nodes Factory Module

创建各类分析师使用的工具节点，将工具配置与主流程解耦。

工具节点类型:
- market: 市场行情工具（K线、指标、估值）
- social: 情绪面工具（资金流向、北向、融资融券）
- news: 新闻面工具（财经新闻、宏观经济）
- fundamentals: 基本面工具（财报、指标、业绩预告）
- china_market: 中国市场制度工具（市场概览、估值分位）
"""

import logging
from typing import Dict, Any

from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


def create_tool_nodes(toolkit) -> Dict[str, ToolNode]:
    """
    创建所有分析师使用的工具节点

    Args:
        toolkit: Toolkit实例，包含所有可用工具

    Returns:
        Dict[str, ToolNode]: 按分析师类型索引的工具节点字典
    """
    return {
        "market": _create_market_tools(toolkit),
        "social": _create_social_tools(toolkit),
        "news": _create_news_tools(toolkit),
        "fundamentals": _create_fundamentals_tools(toolkit),
        "china_market": _create_china_market_tools(toolkit),
    }


def _create_market_tools(toolkit) -> ToolNode:
    """
    市场分析师工具

    职责: 技术面分析（K线、量价、技术指标）
    """
    return ToolNode([
        # 中国A股工具 - 通达信API
        toolkit.get_china_stock_data,
        toolkit.get_china_market_overview,
        # 中国A股基本信息 - Tushare Pro（股票名称+行业）
        toolkit.get_tushare_stock_basic,
        # 中国A股估值工具 - Tushare Pro（PE/PB/市值/换手率）
        toolkit.get_tushare_daily_basic,
        # === 傻瓜化板块工具：自动匹配行业指数 ===
        toolkit.get_sector_benchmark_data,     # 板块对比（自动匹配行业指数）
        # 中国A股扩展工具 - Tushare Pro（板块/期货/解禁）
        toolkit.get_tushare_index_daily,       # 板块指数日线（备用，用于手动指定指数）
        toolkit.get_tushare_fut_daily,         # 期货日线（周期股必用）
        toolkit.get_tushare_share_float,       # 解禁日历（催化剂时点）
        toolkit.get_tushare_adj_factor,        # 复权因子（除权除息分析）
        # 美股/其他市场工具 - Yahoo Finance (online)
        toolkit.get_YFin_data_online,
        toolkit.get_stockstats_indicators_report_online,
        # offline tools
        toolkit.get_YFin_data,
        toolkit.get_stockstats_indicators_report,
    ])


def _create_social_tools(toolkit) -> ToolNode:
    """
    情绪分析师工具

    职责: 资金面分析（主力流向、北向资金、融资融券、筹码结构）
    """
    return ToolNode([
        # 中国A股基本信息 - Tushare Pro（股票名称）
        toolkit.get_tushare_stock_basic,
        # 中国A股情绪工具 - Tushare Pro（高质量数据）
        toolkit.get_tushare_moneyflow,          # 资金流向（大/中/小单）
        # 北向资金工具 - AKShare（Tushare已停更）
        toolkit.get_tushare_hsgt_top10,         # 北向资金十大持股
        toolkit.get_tushare_hsgt_individual,    # 个股北向资金持股历史
        toolkit.get_tushare_margin,             # 融资融券
        toolkit.get_tushare_top10_holders,      # 前十大股东（含"香港中央结算"持股，可替代北向持股分析）
        toolkit.get_tushare_holder_number,      # 股东人数（筹码集中度）
        toolkit.get_tushare_top_list,           # 龙虎榜
        toolkit.get_tushare_sentiment_comprehensive,  # 综合情绪数据包
        toolkit.get_tushare_block_trade,        # 大宗交易数据
        toolkit.get_tushare_pledge_stat,        # 股权质押统计
        # 中国A股情绪工具 - akshare（备用）
        toolkit.get_china_stock_sentiment,
        toolkit.get_china_money_flow,
        # online tools
        toolkit.get_stock_news_openai,
        # offline tools
        toolkit.get_reddit_stock_info,
    ])


def _create_news_tools(toolkit) -> ToolNode:
    """
    新闻分析师工具

    职责: 新闻面分析（公司新闻、行业动态、宏观经济）
    """
    return ToolNode([
        # 中国A股基本信息 - Tushare Pro（股票名称）
        toolkit.get_tushare_stock_basic,
        # 中国财经新闻工具 - akshare
        toolkit.get_china_stock_news,
        toolkit.get_china_market_news,
        # 中国财经新闻工具 - Tushare Pro（优先使用）
        toolkit.get_tushare_cctv_news,          # 新闻联播（政策风向）
        toolkit.get_tushare_market_news,        # 市场新闻（整合新闻联播+重大新闻）
        # 中国宏观经济 - Tushare Pro
        toolkit.get_tushare_pmi,                # PMI采购经理指数
        # online tools
        toolkit.get_global_news_openai,
        toolkit.get_google_news,
        # offline tools
        toolkit.get_finnhub_news,
        toolkit.get_reddit_news,
    ])


def _create_fundamentals_tools(toolkit) -> ToolNode:
    """
    基本面分析师工具

    职责: 基本面分析（财务报表、指标分析、业绩预告）
    """
    return ToolNode([
        # 中国A股基本面工具 - Tushare Pro（高质量数据，优先使用）
        toolkit.get_tushare_financial_statements,      # 财务三表（利润表/资产负债表/现金流）
        toolkit.get_tushare_financial_indicators,      # 财务指标（150+指标）
        toolkit.get_tushare_daily_basic,               # 每日估值（PE/PB/市值）
        toolkit.get_tushare_forecast,                  # 业绩预告
        toolkit.get_tushare_dividend,                  # 分红历史
        toolkit.get_tushare_stock_basic,               # 股票基本信息（准确名称）
        toolkit.get_tushare_fundamentals_comprehensive, # 基本面综合数据包
        toolkit.get_tushare_stk_surv,                  # 机构调研数据
        toolkit.get_tushare_report_rc,                 # 券商研报数据
        toolkit.get_tushare_index_member,              # 行业成分股（用于同行对比）
        # 中国A股基本面工具 - akshare（备用）
        toolkit.get_china_financial_report,
        toolkit.get_china_stock_indicators,
        toolkit.get_china_earnings_forecast,
        # online tools
        toolkit.get_fundamentals_openai,
        # offline tools
        toolkit.get_finnhub_company_insider_sentiment,
        toolkit.get_finnhub_company_insider_transactions,
        toolkit.get_simfin_balance_sheet,
        toolkit.get_simfin_cashflow,
        toolkit.get_simfin_income_stmt,
    ])


def _create_china_market_tools(toolkit) -> ToolNode:
    """
    中国市场制度分析师工具

    职责: 制度面分析（市场风格、政策环境、板块轮动）
    """
    return ToolNode([
        # 中国A股数据 - 通达信API（行情数据）
        toolkit.get_china_stock_data,
        toolkit.get_china_market_overview,
        # 中国A股数据 - Tushare Pro（估值数据）
        toolkit.get_tushare_daily_basic,
        toolkit.get_tushare_stock_basic,
        # 备用数据源
        toolkit.get_YFin_data_online,
        toolkit.get_stockstats_indicators_report_online,
    ])


def get_tool_node_summary() -> Dict[str, Dict[str, Any]]:
    """
    获取工具节点摘要信息（用于文档和调试）

    Returns:
        Dict: 每个节点类型的工具数量和用途说明
    """
    return {
        "market": {
            "count": 13,  # 添加了sector_benchmark_data, adj_factor
            "purpose": "技术面分析",
            "data_sources": ["通达信", "Tushare Pro", "Yahoo Finance"],
        },
        "social": {
            "count": 15,  # 添加了hsgt_individual（个股北向持股）
            "purpose": "资金面/情绪面分析",
            "data_sources": ["Tushare Pro", "AKShare", "Reddit"],
        },
        "news": {
            "count": 8,
            "purpose": "新闻面/宏观分析",
            "data_sources": ["AKShare", "Tushare Pro", "Google News", "Finnhub"],
        },
        "fundamentals": {
            "count": 19,  # 添加了stk_surv, report_rc, index_member
            "purpose": "基本面分析",
            "data_sources": ["Tushare Pro", "AKShare", "SimFin", "Finnhub"],
        },
        "china_market": {
            "count": 6,
            "purpose": "市场制度/政策分析",
            "data_sources": ["通达信", "Tushare Pro"],
        },
    }
