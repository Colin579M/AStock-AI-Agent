"""
Chatbot 工具注册表

提供 Chatbot 使用的工具集合，从现有 Toolkit 中提取核心工具。

Phase 1: 5 个核心工具
Phase 2: 扩展到 20+ 工具
"""
from typing import List, Optional
from langchain_core.tools import tool, BaseTool
from typing import Annotated


# ============================================================================
# Phase 1 核心工具（5个）
# ============================================================================

@tool
def get_stock_basic_info(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取股票基本信息，包括代码、名称、全称、行业、地区、上市日期等。
    这是获取股票准确名称和基本属性的可靠数据源。

    示例：
    - get_stock_basic_info("600036") -> 返回招商银行基本信息
    - get_stock_basic_info("000001") -> 返回平安银行基本信息
    """
    from tradingagents.dataflows.tushare_utils import get_stock_basic_info as _get_stock_basic_info
    return _get_stock_basic_info(stock_code)


@tool
def get_stock_valuation(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"],
    trade_date: Annotated[str, "交易日期 YYYYMMDD 格式，留空获取最近数据"] = ""
) -> str:
    """
    获取每日估值指标，包括 PE(TTM)、PB、PS、总市值、流通市值、换手率、量比。
    提供更准确的实时估值数据，支持历史估值对比分析。

    示例：
    - get_stock_valuation("600036") -> 返回招商银行最近的估值指标
    - get_stock_valuation("600036", "20260110") -> 返回指定日期的估值指标
    """
    from tradingagents.dataflows.tushare_utils import get_daily_basic
    return get_daily_basic(stock_code, trade_date if trade_date else None)


@tool
def get_stock_moneyflow(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取个股资金流向，按大单/中单/小单分类统计净流入流出。
    提供更精细的资金分类（5万/20万/100万分界），准确反映主力资金动向。

    示例：
    - get_stock_moneyflow("600036") -> 返回招商银行近10日资金流向
    """
    from tradingagents.dataflows.tushare_utils import get_moneyflow
    return get_moneyflow(stock_code)


@tool
def get_market_news(
    date: Annotated[str, "日期，格式 YYYYMMDD 或 YYYY-MM-DD，默认今天"] = ""
) -> str:
    """
    获取新闻联播文字稿，筛选经济相关内容。
    新闻联播是重要的政策风向标，关注经济、金融、产业相关内容有助于把握政策方向。

    示例：
    - get_market_news() -> 返回今天的新闻联播经济要点
    - get_market_news("20260110") -> 返回指定日期的新闻
    """
    from tradingagents.dataflows.tushare_utils import get_cctv_news
    if date:
        date = date.replace("-", "")
    return get_cctv_news(date if date else None)


@tool
def get_stock_fundamentals(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取A股基本面综合数据包，一次性返回财务报表、财务指标、业绩预告、分红历史。
    这是进行基本面分析的一站式数据源，适合全面评估公司价值。

    示例：
    - get_stock_fundamentals("600036") -> 返回招商银行基本面综合分析
    """
    from tradingagents.dataflows.tushare_utils import get_china_stock_fundamentals
    return get_china_stock_fundamentals(stock_code)


# ============================================================================
# Phase 2 扩展工具 - 财务分析类（5个）
# ============================================================================

@tool
def get_financial_statements(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取财务报表数据，包括利润表、资产负债表、现金流量表的核心指标。
    适合深入分析公司盈利能力、偿债能力和现金流状况。

    示例：
    - get_financial_statements("600036") -> 返回招商银行财务报表
    """
    from tradingagents.dataflows.tushare_utils import get_financial_statements as _get_financial_statements
    return _get_financial_statements(stock_code)


@tool
def get_financial_indicators(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取财务指标数据（5年历史+近4季详细），支持周期股估值分析。

    返回内容：
    1. 历史指标摘要（5年/20季度）：EPS/ROE/毛利率的平均值、最高、最低及周期位置
    2. 近4季详细数据：盈利能力、每股指标、偿债能力、增长率

    示例：
    - get_financial_indicators("601088") -> 返回中国神华财务指标（含周期位置判断）
    """
    from tradingagents.dataflows.tushare_utils import get_financial_indicators as _get_financial_indicators
    return _get_financial_indicators(stock_code)


@tool
def get_forecast(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取业绩预告数据，包括预告类型（预增/预减/扭亏/首亏等）、预告净利润范围。
    适合提前了解公司业绩变动趋势。

    示例：
    - get_forecast("600036") -> 返回招商银行业绩预告
    """
    from tradingagents.dataflows.tushare_utils import get_forecast as _get_forecast
    return _get_forecast(stock_code)


@tool
def get_dividend(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取分红送股历史，包括每股派息、送股比例、转增比例、除权除息日。
    适合评估公司分红政策和股东回报。

    示例：
    - get_dividend("600036") -> 返回招商银行分红历史
    """
    from tradingagents.dataflows.tushare_utils import get_dividend as _get_dividend
    return _get_dividend(stock_code)


@tool
def get_pledge_stat(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取股权质押统计，包括质押股数、质押比例、解押情况。
    质押比例过高可能存在平仓风险，是重要的风险指标。

    示例：
    - get_pledge_stat("600036") -> 返回招商银行股权质押情况
    """
    from tradingagents.dataflows.tushare_utils import get_pledge_stat as _get_pledge_stat
    return _get_pledge_stat(stock_code)


# ============================================================================
# Phase 2 扩展工具 - 持股/资金类（5个）
# ============================================================================

@tool
def get_top10_holders(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取前十大股东信息，包括股东名称、持股数量、持股比例、股东性质。
    适合了解公司股权结构和主要股东变动。

    示例：
    - get_top10_holders("600036") -> 返回招商银行前十大股东
    """
    from tradingagents.dataflows.tushare_utils import get_top10_holders as _get_top10_holders
    return _get_top10_holders(stock_code)


@tool
def get_holder_number(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取股东人数变化，包括股东户数、户均持股、股东人数增减。
    股东人数减少通常意味着筹码集中，是判断主力动向的重要指标。

    示例：
    - get_holder_number("600036") -> 返回招商银行股东人数变化
    """
    from tradingagents.dataflows.tushare_utils import get_holder_number as _get_holder_number
    return _get_holder_number(stock_code)


@tool
def get_hsgt_flow() -> str:
    """
    获取沪深港通资金流向，包括北向资金整体流向和持股排行。
    北向资金被视为"聪明钱"，其流向是重要的市场情绪指标。

    注意：2024年8月19日起，交易所调整披露机制，整体流向数据已停更，
    但持股排行和个股持股数据仍可查询。

    示例：
    - get_hsgt_flow() -> 返回北向资金流向和持股排行
    """
    from tradingagents.dataflows.akshare_utils import get_hsgt_flow as _get_hsgt_flow
    return _get_hsgt_flow()


@tool
def get_hsgt_top10(
    trade_date: Annotated[str, "交易日期 YYYYMMDD 格式，留空获取最近数据"] = ""
) -> str:
    """
    获取北向资金十大持股股，包括持股市值排名、今日增减持排名。
    可以看出外资最关注的个股标的。

    示例：
    - get_hsgt_top10() -> 返回北向资金十大持股
    - get_hsgt_top10("20260110") -> 返回指定日期的数据
    """
    from tradingagents.dataflows.akshare_utils import get_hsgt_top10 as _get_hsgt_top10
    return _get_hsgt_top10(trade_date if trade_date else None)


@tool
def get_hsgt_individual(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取个股北向资金持股历史，包括持股数量、持股市值、增减持变化。
    可以追踪外资对某只股票的持仓变化趋势。

    示例：
    - get_hsgt_individual("600036") -> 返回招商银行北向资金持股历史
    """
    from tradingagents.dataflows.akshare_utils import get_hsgt_individual as _get_hsgt_individual
    return _get_hsgt_individual(stock_code)


@tool
def get_margin_data(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取融资融券数据，包括融资余额、融券余额、融资买入额。
    融资余额增加表示杠杆资金看多，是市场情绪的重要指标。

    示例：
    - get_margin_data("600036") -> 返回招商银行融资融券数据
    """
    from tradingagents.dataflows.tushare_utils import get_margin_data as _get_margin_data
    return _get_margin_data(stock_code)


# ============================================================================
# Phase 2 扩展工具 - 市场活动类（3个）
# ============================================================================

@tool
def get_top_list(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"],
    days: Annotated[int, "查询天数，默认30"] = 30
) -> str:
    """
    获取龙虎榜数据，包括上榜原因、买入前五/卖出前五营业部、净买入金额。
    龙虎榜反映游资和机构的短期博弈，是短线交易的重要参考。

    示例：
    - get_top_list("600036") -> 返回招商银行近30日龙虎榜
    """
    from tradingagents.dataflows.tushare_utils import get_top_list as _get_top_list
    return _get_top_list(stock_code, days)


@tool
def get_block_trade(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"],
    days: Annotated[int, "查询天数，默认30"] = 30
) -> str:
    """
    获取大宗交易数据，包括成交价、成交量、折溢价率、买卖营业部。
    大宗交易折价过大可能暗示抛压，是判断大资金动向的参考。

    示例：
    - get_block_trade("600036") -> 返回招商银行近30日大宗交易
    """
    from tradingagents.dataflows.tushare_utils import get_block_trade as _get_block_trade
    return _get_block_trade(stock_code, days)


@tool
def get_share_float(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取限售股解禁计划，包括解禁日期、解禁股数、解禁类型。
    大规模解禁前需要关注潜在抛压风险。

    示例：
    - get_share_float("600036") -> 返回招商银行解禁计划
    """
    from tradingagents.dataflows.tushare_utils import get_share_float as _get_share_float
    return _get_share_float(stock_code)


# ============================================================================
# Phase 2 扩展工具 - 排行榜类（3个）
# ============================================================================

@tool
def get_stock_ranking(
    rank_type: Annotated[str, "排行类型: 涨幅榜/跌幅榜/成交额榜/换手率榜/资金流入榜/资金流出榜"],
    period: Annotated[str, "时间周期: 今日/5日/10日/20日，默认今日"] = "今日",
    market: Annotated[str, "市场范围: 全部/沪市/深市/创业板/科创板，默认全部"] = "全部",
    top_n: Annotated[int, "返回前N名，默认20"] = 20
) -> str:
    """
    获取 A 股排行榜，包括涨幅榜、跌幅榜、成交额榜、换手率榜、资金流向榜。
    这是查询热门股票、活跃股票的主要工具。

    示例：
    - get_stock_ranking("涨幅榜") -> 返回今日涨幅前20
    - get_stock_ranking("成交额榜", top_n=10) -> 返回今日成交额前10
    - get_stock_ranking("资金流入榜", "5日") -> 返回5日主力资金净流入前20
    - get_stock_ranking("换手率榜", market="创业板") -> 返回创业板换手率前20
    """
    from tradingagents.dataflows.akshare_utils import get_stock_rank
    return get_stock_rank(rank_type, period, market, top_n)


@tool
def get_hot_stocks_list(
    top_n: Annotated[int, "返回前N名，默认20"] = 20
) -> str:
    """
    获取热门股票排行，综合人气榜和成交额数据。
    适合快速了解市场当前最受关注的股票。

    示例：
    - get_hot_stocks_list() -> 返回热门股票前20
    - get_hot_stocks_list(10) -> 返回热门股票前10
    """
    from tradingagents.dataflows.akshare_utils import get_hot_stocks
    return get_hot_stocks(top_n)


@tool
def get_continuous_rise_stocks(
    days: Annotated[int, "连涨天数，默认3"] = 3,
    top_n: Annotated[int, "返回前N名，默认20"] = 20
) -> str:
    """
    获取连续上涨的股票，按连涨天数和累计涨幅排序。
    适合发现持续走强的股票。

    示例：
    - get_continuous_rise_stocks() -> 返回连涨3天以上的股票
    - get_continuous_rise_stocks(5) -> 返回连涨5天以上的股票
    """
    from tradingagents.dataflows.akshare_utils import get_continuous_up_stocks
    return get_continuous_up_stocks(days, top_n)


# ============================================================================
# Phase 2 扩展工具 - 板块数据（1个）
# ============================================================================

@tool
def get_sector_ranking(
    indicator: Annotated[str, "板块类型：行业/概念/地域，默认行业"] = "行业"
) -> str:
    """
    获取板块涨跌幅排行，包括行业板块、概念板块、地域板块。
    适合查看哪些板块在领涨/领跌，分析市场热点和资金流向。

    板块类型说明：
    - 行业：按申万行业分类（84个行业）
    - 概念：按题材概念分类（如AI、新能源等）
    - 地域：按地区分类（如北京、上海等）

    示例：
    - get_sector_ranking("行业") -> 返回行业板块涨跌幅排行
    - get_sector_ranking("概念") -> 返回概念板块涨跌幅排行
    """
    from tradingagents.dataflows.akshare_utils import get_sector_ranking as _get_sector_ranking
    return _get_sector_ranking(indicator)


# ============================================================================
# Phase 2 扩展工具 - 指数/宏观类（2个）
# ============================================================================

@tool
def get_index_daily(
    index_code: Annotated[str, "指数代码，如 000001.SH(上证指数), 399001.SZ(深证成指), 399006.SZ(创业板指)"],
    days: Annotated[int, "查询天数，默认60"] = 60
) -> str:
    """
    获取指数日线数据，包括开盘、收盘、最高、最低、成交量、涨跌幅。
    适合分析大盘走势和市场整体状态。

    常用指数代码：
    - 000001.SH: 上证指数
    - 399001.SZ: 深证成指
    - 399006.SZ: 创业板指
    - 000300.SH: 沪深300
    - 000016.SH: 上证50
    - 000905.SH: 中证500

    示例：
    - get_index_daily("000001.SH") -> 返回上证指数近60日走势
    """
    from tradingagents.dataflows.tushare_utils import get_index_daily as _get_index_daily
    return _get_index_daily(index_code, days)


@tool
def get_pmi() -> str:
    """
    获取中国制造业PMI数据，PMI>50表示经济扩张，<50表示收缩。
    PMI是重要的宏观经济先行指标，对市场走势有指导意义。

    示例：
    - get_pmi() -> 返回近期PMI数据
    """
    from tradingagents.dataflows.tushare_utils import get_pmi as _get_pmi
    return _get_pmi()


# ============================================================================
# Phase 2 扩展工具 - 机构/公告类（2个）
# ============================================================================

@tool
def get_report_rc(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"],
    days: Annotated[int, "查询天数，默认30"] = 30
) -> str:
    """
    获取券商研报评级，包括评级（买入/增持/中性等）、目标价、研究机构、分析师。
    券商评级代表机构观点，可作为投资参考（但需独立判断）。

    示例：
    - get_report_rc("600036") -> 返回招商银行近30日券商评级
    """
    from tradingagents.dataflows.tushare_utils import get_report_rc as _get_report_rc
    return _get_report_rc(stock_code, days)


@tool
def get_stk_surv(
    stock_code: Annotated[str, "股票代码，如 600036, 000001"]
) -> str:
    """
    获取业绩快报和公告信息，包括营收、净利润、EPS等季度数据。
    业绩快报比正式财报更早发布，可以提前了解业绩情况。

    示例：
    - get_stk_surv("600036") -> 返回招商银行业绩快报
    """
    from tradingagents.dataflows.tushare_utils import get_stk_surv as _get_stk_surv
    return _get_stk_surv(stock_code)


# ============================================================================
# 工具加载函数
# ============================================================================

def load_core_tools() -> List[BaseTool]:
    """
    加载 Phase 1 核心工具（5个）

    Returns:
        List[BaseTool]: 核心工具列表
    """
    return [
        get_stock_basic_info,
        get_stock_valuation,
        get_stock_moneyflow,
        get_market_news,
        get_stock_fundamentals,
    ]


def load_quick_tools() -> List[BaseTool]:
    """
    加载 QuickAgent 专用工具集（7个）

    精简工具集，专为简单查询优化：
    - 基本信息、估值指标、指数走势
    - 排行榜、热门股票
    - 报告查询

    Returns:
        List[BaseTool]: QuickAgent 工具列表
    """
    from .report_tools import list_available_reports, get_analysis_report

    return [
        get_stock_basic_info,      # 股票基本信息
        get_stock_valuation,       # 估值指标
        get_index_daily,           # 指数走势（大盘查询必需）
        get_stock_ranking,         # 排行榜
        get_hot_stocks_list,       # 热门股票
        get_market_news,           # 新闻
        list_available_reports,    # 报告列表查询
        get_analysis_report,       # 报告内容查询
    ]


def load_analysis_tools() -> List[BaseTool]:
    """
    加载 AnalysisAgent 工具集（18个）

    中等规模工具集，用于深度分析：
    - 包含所有 Quick 工具
    - 增加财务、资金、机构相关工具

    Returns:
        List[BaseTool]: AnalysisAgent 工具列表
    """
    from .report_tools import list_available_reports, get_analysis_report, compare_reports

    return [
        # 基础工具（来自 Quick）
        get_stock_basic_info,
        get_stock_valuation,
        get_index_daily,
        get_stock_ranking,
        get_market_news,
        # 资金流向
        get_stock_moneyflow,
        get_hsgt_flow,
        get_hsgt_top10,
        get_margin_data,
        # 财务分析
        get_stock_fundamentals,
        get_financial_statements,
        get_financial_indicators,
        get_forecast,
        # 持股结构
        get_top10_holders,
        get_holder_number,
        # 机构观点
        get_report_rc,
        # 报告工具
        list_available_reports,
        get_analysis_report,
        compare_reports,
    ]


def load_unified_tools() -> List[BaseTool]:
    """
    加载 UnifiedAgent 统一工具集（16个）

    精选核心工具，覆盖 90% 使用场景：
    - 基础信息（3个）
    - 资金流向（3个）
    - 财务数据（3个）
    - 市场数据（4个）
    - 报告查询（3个）

    Returns:
        List[BaseTool]: UnifiedAgent 工具列表
    """
    from .report_tools import list_available_reports, get_analysis_report, compare_reports

    return [
        # 基础信息（3个）
        get_stock_basic_info,      # 股票基本信息
        get_stock_valuation,       # 估值指标（PE/PB/市值）
        get_index_daily,           # 指数走势（大盘查询必需）

        # 资金流向（3个）
        get_stock_moneyflow,       # 个股资金流向
        get_hsgt_flow,             # 北向资金流向
        get_margin_data,           # 融资融券数据

        # 财务数据（3个）
        get_stock_fundamentals,    # 基本面综合数据
        get_financial_indicators,  # 财务指标（ROE/毛利率等）
        get_forecast,              # 业绩预告

        # 市场数据（4个）
        get_stock_ranking,         # 排行榜（涨跌幅/成交额等）
        get_hot_stocks_list,       # 热门股票
        get_market_news,           # 新闻联播要点
        get_sector_ranking,        # 板块排行（行业/概念/地域）

        # 报告查询（3个）
        list_available_reports,    # 历史报告列表
        get_analysis_report,       # 报告内容查询
        compare_reports,           # 报告对比
    ]


def load_all_tools() -> List[BaseTool]:
    """
    加载所有可用工具（Phase 2: 23个 + 报告工具: 3个 = 26个）

    Returns:
        List[BaseTool]: 完整工具列表
    """
    from .report_tools import REPORT_TOOLS

    return [
        # Phase 1 核心工具（5个）
        get_stock_basic_info,
        get_stock_valuation,
        get_stock_moneyflow,
        get_market_news,
        get_stock_fundamentals,
        # Phase 2 财务分析类（5个）
        get_financial_statements,
        get_financial_indicators,
        get_forecast,
        get_dividend,
        get_pledge_stat,
        # Phase 2 持股/资金类（6个）- 北向资金使用 AKShare
        get_top10_holders,
        get_holder_number,
        get_hsgt_flow,           # AKShare
        get_hsgt_top10,          # AKShare
        get_hsgt_individual,     # AKShare - 新增个股北向持股
        get_margin_data,
        # Phase 2 市场活动类（3个）
        get_top_list,
        get_block_trade,
        get_share_float,
        # Phase 2 排行榜类（3个）- 新增
        get_stock_ranking,
        get_hot_stocks_list,
        get_continuous_rise_stocks,
        # Phase 2 指数/宏观类（2个）
        get_index_daily,
        get_pmi,
        # Phase 2 机构/公告类（2个）
        get_report_rc,
        get_stk_surv,
    ] + REPORT_TOOLS  # 报告查询工具（3个）


def get_tool_by_name(name: str) -> Optional[BaseTool]:
    """
    根据名称获取工具

    Args:
        name: 工具名称

    Returns:
        BaseTool 或 None
    """
    tools = {t.name: t for t in load_all_tools()}
    return tools.get(name)


# ============================================================================
# 工具描述（用于 LLM 选择）
# ============================================================================

TOOL_DESCRIPTIONS = {
    # Phase 1 核心工具
    "get_stock_basic_info": "获取股票基本信息（名称、行业、上市日期等）",
    "get_stock_valuation": "获取股票估值指标（PE、PB、市值、换手率等）",
    "get_stock_moneyflow": "获取资金流向（大单、中单、小单净流入）",
    "get_market_news": "获取新闻联播经济要点",
    "get_stock_fundamentals": "获取基本面综合数据（财报、指标、预告、分红）",
    # Phase 2 财务分析类
    "get_financial_statements": "获取财务报表（利润表、资产负债表、现金流量表）",
    "get_financial_indicators": "获取财务指标（5年历史+近4季详细，含周期位置判断）",
    "get_forecast": "获取业绩预告（预增/预减/扭亏/首亏等）",
    "get_dividend": "获取分红送股历史",
    "get_pledge_stat": "获取股权质押统计",
    # Phase 2 持股/资金类（北向资金使用 AKShare）
    "get_top10_holders": "获取前十大股东信息",
    "get_holder_number": "获取股东人数变化",
    "get_hsgt_flow": "获取北向资金流向和持股排行（AKShare）",
    "get_hsgt_top10": "获取北向资金十大持股和增减持排行（AKShare）",
    "get_hsgt_individual": "获取个股北向资金持股历史（AKShare）",
    "get_margin_data": "获取融资融券数据",
    # Phase 2 市场活动类
    "get_top_list": "获取龙虎榜数据",
    "get_block_trade": "获取大宗交易数据",
    "get_share_float": "获取限售股解禁计划",
    # Phase 2 排行榜类（新增）
    "get_stock_ranking": "获取A股排行榜（涨幅/跌幅/成交额/换手率/资金流向）",
    "get_hot_stocks_list": "获取热门股票排行（人气榜+成交额）",
    "get_continuous_rise_stocks": "获取连续上涨的股票",
    # Phase 2 指数/宏观类
    "get_index_daily": "获取指数日线数据",
    "get_pmi": "获取制造业PMI数据",
    # Phase 2 机构/公告类
    "get_report_rc": "获取券商研报评级",
    "get_stk_surv": "获取业绩快报和公告",
    # 报告查询工具
    "list_available_reports": "列出股票的所有历史分析报告",
    "get_analysis_report": "获取指定股票的历史分析报告内容",
    "compare_reports": "对比同一股票不同日期的分析报告",
}
