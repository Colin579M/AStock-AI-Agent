# tradingagents/dataflows/akshare_utils.py
"""
中国A股数据获取工具 - 基于 akshare
提供财报数据、新闻数据、情绪数据获取功能
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import traceback
import threading
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 全 A 股数据缓存（排行榜等功能使用）
# ============================================================================

class StockDataCache:
    """A股实时行情缓存，避免重复调用耗时 API"""

    def __init__(self, ttl_seconds: int = 300):  # 默认5分钟缓存
        self._cache = None
        self._cache_time = None
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get_all_stocks(self) -> pd.DataFrame:
        """获取全 A 股实时行情（带缓存）"""
        with self._lock:
            now = datetime.now()

            # 检查缓存是否有效
            if self._cache is not None and self._cache_time is not None:
                age = (now - self._cache_time).total_seconds()
                if age < self._ttl:
                    logger.debug(f"使用缓存数据 (age={age:.1f}s)")
                    return self._cache.copy()

            # 缓存过期或不存在，重新获取
            logger.info("获取全 A 股实时行情...")
            try:
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    self._cache = df
                    self._cache_time = now
                    logger.info(f"缓存更新成功，共 {len(df)} 只股票")
                    return df.copy()
            except Exception as e:
                logger.error(f"获取 A 股数据失败: {e}")
                # 如果有旧缓存，返回旧数据
                if self._cache is not None:
                    logger.warning("使用过期缓存数据")
                    return self._cache.copy()

            return pd.DataFrame()

    def clear(self):
        """清除缓存"""
        with self._lock:
            self._cache = None
            self._cache_time = None


# 全局缓存实例
_stock_cache = StockDataCache(ttl_seconds=300)  # 5分钟缓存

# 预热状态标记
_cache_prewarm_started = False
_cache_prewarm_thread = None


def get_cached_stock_data() -> pd.DataFrame:
    """获取缓存的 A 股数据"""
    return _stock_cache.get_all_stocks()


def prewarm_stock_cache() -> bool:
    """
    预热股票数据缓存（同步调用）

    Returns:
        bool: 是否成功
    """
    try:
        logger.info("开始预热 A 股数据缓存...")
        df = _stock_cache.get_all_stocks()
        if df is not None and not df.empty:
            logger.info(f"A 股数据缓存预热完成，共 {len(df)} 只股票")
            return True
        return False
    except Exception as e:
        logger.warning(f"缓存预热失败: {e}")
        return False


def prewarm_stock_cache_async():
    """
    后台异步预热股票数据缓存

    在后台线程中预热缓存，不阻塞主线程。
    """
    import threading
    global _cache_prewarm_started, _cache_prewarm_thread

    if _cache_prewarm_started:
        return  # 已经在预热中

    _cache_prewarm_started = True

    def _prewarm():
        try:
            prewarm_stock_cache()
        except Exception as e:
            logger.warning(f"后台缓存预热失败: {e}")

    _cache_prewarm_thread = threading.Thread(target=_prewarm, daemon=True)
    _cache_prewarm_thread.start()
    logger.info("后台缓存预热已启动")


# 常见股票名称别名/错别字映射
STOCK_NAME_ALIASES = {
    # 常见简称
    "茅台": "贵州茅台",
    "五粮液": "五粮液",
    "比亚迪": "比亚迪",
    "宁德": "宁德时代",
    "招行": "招商银行",
    "平安": "中国平安",
    "腾讯": None,  # 不在A股
    "阿里": None,  # 不在A股
    "阿里巴巴": None,  # 不在A股
    # 常见错别字
    "毛台": "贵州茅台",
    "贵州毛台": "贵州茅台",
    "宁得时代": "宁德时代",
    "宁德时代": "宁德时代",
    "比亚笛": "比亚迪",
    "招商银行": "招商银行",
    "招商银航": "招商银行",
    "东方财付": "东方财富",
}


def fuzzy_match_stock_name(query: str) -> Optional[str]:
    """
    模糊匹配股票名称，纠正错别字

    Args:
        query: 用户输入的查询（可能包含错别字）

    Returns:
        匹配到的股票名称，或 None
    """
    # 先检查别名表
    for alias, real_name in STOCK_NAME_ALIASES.items():
        if alias in query:
            return real_name

    # 如果没有匹配，尝试从缓存数据中模糊搜索
    df = get_cached_stock_data()
    if df is None or df.empty:
        return None

    # 检查完全匹配
    if '名称' in df.columns:
        exact_match = df[df['名称'] == query]
        if not exact_match.empty:
            return query

        # 部分匹配
        partial_match = df[df['名称'].str.contains(query, na=False)]
        if not partial_match.empty:
            return partial_match.iloc[0]['名称']

    return None


# ============================================================================
# 阶段 1：财报数据获取
# ============================================================================

def get_financial_report(stock_code: str, report_type: str = "all") -> str:
    """
    获取中国A股财务报表（使用新浪财经接口）

    Args:
        stock_code: 股票代码，如 "601899"
        report_type: 报表类型 - "balance"(资产负债表), "income"(利润表),
                     "cashflow"(现金流量表), "all"(全部)

    Returns:
        str: 格式化的财务报表数据
    """
    try:
        result_parts = []

        # 确定市场前缀（上海sh，深圳sz）
        if stock_code.startswith('6'):
            stock_symbol = f"sh{stock_code}"
        else:
            stock_symbol = f"sz{stock_code}"

        if report_type in ["balance", "all"]:
            try:
                # 获取资产负债表（新浪财经接口）
                # 数据格式：行=报告期（如20250930），列=财务项目
                df_balance = ak.stock_financial_report_sina(stock=stock_symbol, symbol="资产负债表")
                if df_balance is not None and not df_balance.empty:
                    result_parts.append("## 资产负债表（最近4期）\n")

                    # 选择关键列
                    key_cols = ['报告日', '货币资金', '流动资产', '非流动资产合计',
                               '资产总计', '流动负债合计', '非流动负债合计',
                               '负债合计', '所有者权益合计']
                    available_cols = [c for c in key_cols if c in df_balance.columns]
                    if available_cols:
                        result_parts.append(df_balance.head(4)[available_cols].to_markdown(index=False))
                    else:
                        result_parts.append(df_balance.head(4).iloc[:, :8].to_markdown(index=False))
                    result_parts.append("\n")
            except Exception as e:
                result_parts.append(f"资产负债表获取失败: {str(e)}\n")

        if report_type in ["income", "all"]:
            try:
                # 获取利润表（新浪财经接口）
                df_income = ak.stock_financial_report_sina(stock=stock_symbol, symbol="利润表")
                if df_income is not None and not df_income.empty:
                    result_parts.append("## 利润表（最近4期）\n")

                    key_cols = ['报告日', '营业收入', '营业成本', '营业利润',
                               '利润总额', '净利润', '归属于母公司所有者的净利润',
                               '基本每股收益']
                    available_cols = [c for c in key_cols if c in df_income.columns]
                    if available_cols:
                        result_parts.append(df_income.head(4)[available_cols].to_markdown(index=False))
                    else:
                        result_parts.append(df_income.head(4).iloc[:, :8].to_markdown(index=False))
                    result_parts.append("\n")
            except Exception as e:
                result_parts.append(f"利润表获取失败: {str(e)}\n")

        if report_type in ["cashflow", "all"]:
            try:
                # 获取现金流量表（新浪财经接口）
                df_cashflow = ak.stock_financial_report_sina(stock=stock_symbol, symbol="现金流量表")
                if df_cashflow is not None and not df_cashflow.empty:
                    result_parts.append("## 现金流量表（最近4期）\n")

                    key_cols = ['报告日', '经营活动产生的现金流量净额',
                               '投资活动产生的现金流量净额', '筹资活动产生的现金流量净额',
                               '现金及现金等价物净增加额']
                    available_cols = [c for c in key_cols if c in df_cashflow.columns]
                    if available_cols:
                        result_parts.append(df_cashflow.head(4)[available_cols].to_markdown(index=False))
                    else:
                        result_parts.append(df_cashflow.head(4).iloc[:, :6].to_markdown(index=False))
                    result_parts.append("\n")
            except Exception as e:
                result_parts.append(f"现金流量表获取失败: {str(e)}\n")

        if result_parts:
            return f"# {stock_code} 财务报表\n\n" + "\n".join(result_parts)
        else:
            return f"无法获取 {stock_code} 的财务报表数据"

    except Exception as e:
        return f"获取财务报表时发生错误: {str(e)}\n{traceback.format_exc()}"


def get_stock_indicators(stock_code: str) -> str:
    """
    获取中国A股核心指标（PE/PB/ROE/市值等）

    Args:
        stock_code: 股票代码

    Returns:
        str: 格式化的核心指标数据
    """
    try:
        result_parts = []
        result_parts.append(f"# {stock_code} 核心财务指标\n")

        # 获取财务摘要（包含历史关键指标）
        try:
            df_abstract = ak.stock_financial_abstract(symbol=stock_code)
            if df_abstract is not None and not df_abstract.empty:
                result_parts.append("## 财务摘要（关键指标）\n")

                # 筛选常用指标行
                key_indicators = ['归母净利润', '营业总收入', '营业成本', '净利润',
                                 '毛利率', '净利率', '净资产收益率', '资产负债率',
                                 '每股收益', '每股净资产']
                if '选项' in df_abstract.columns and '指标' in df_abstract.columns:
                    df_filtered = df_abstract[df_abstract['指标'].isin(key_indicators)]
                    if not df_filtered.empty:
                        # 只保留最近4期数据
                        cols_to_keep = list(df_filtered.columns[:2]) + list(df_filtered.columns[2:6])
                        result_parts.append(df_filtered[cols_to_keep].to_markdown(index=False))
                    else:
                        result_parts.append(df_abstract.head(10).iloc[:, :6].to_markdown(index=False))
                else:
                    result_parts.append(df_abstract.head(10).iloc[:, :6].to_markdown(index=False))
                result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"财务摘要获取失败: {str(e)}\n")

        # 获取实时行情数据（包含PE/PB/市值）- 这个比较慢，作为备选
        try:
            df_spot = ak.stock_zh_a_spot_em()
            if df_spot is not None and not df_spot.empty:
                # 查找目标股票
                stock_row = df_spot[df_spot['代码'] == stock_code]
                if not stock_row.empty:
                    result_parts.append("## 实时估值数据\n")
                    cols_to_show = ['代码', '名称', '最新价', '涨跌幅', '市盈率-动态',
                                   '市净率', '总市值', '流通市值', '换手率', '量比',
                                   '60日涨跌幅', '年初至今涨跌幅']
                    available_cols = [c for c in cols_to_show if c in stock_row.columns]
                    if available_cols:
                        result_parts.append(stock_row[available_cols].to_markdown(index=False))
                    result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"实时估值数据获取失败: {str(e)}\n")

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取核心指标时发生错误: {str(e)}\n{traceback.format_exc()}"


def get_earnings_forecast(stock_code: str) -> str:
    """
    获取中国A股业绩预告

    Args:
        stock_code: 股票代码

    Returns:
        str: 格式化的业绩预告数据
    """
    try:
        result_parts = []
        result_parts.append(f"# {stock_code} 业绩预告与报告\n")

        # 获取业绩预告
        try:
            df_forecast = ak.stock_yjyg_em()
            if df_forecast is not None and not df_forecast.empty:
                # 筛选目标股票
                stock_forecast = df_forecast[df_forecast['股票代码'] == stock_code]
                if not stock_forecast.empty:
                    result_parts.append("## 业绩预告\n")
                    result_parts.append(stock_forecast.head(4).to_markdown(index=False))
                    result_parts.append("\n")
                else:
                    result_parts.append("## 业绩预告\n暂无该股票的业绩预告数据\n")
        except Exception as e:
            result_parts.append(f"业绩预告获取失败: {str(e)}\n")

        # 获取业绩报表
        try:
            df_report = ak.stock_yjbb_em()
            if df_report is not None and not df_report.empty:
                stock_report = df_report[df_report['股票代码'] == stock_code]
                if not stock_report.empty:
                    result_parts.append("## 业绩报表\n")
                    cols_to_show = ['股票代码', '股票简称', '每股收益', '营业收入',
                                   '营业收入同比增长', '净利润', '净利润同比增长',
                                   '净资产收益率', '报告期']
                    available_cols = [c for c in cols_to_show if c in stock_report.columns]
                    if available_cols:
                        result_parts.append(stock_report[available_cols].head(4).to_markdown(index=False))
                    else:
                        result_parts.append(stock_report.head(4).to_markdown(index=False))
                    result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"业绩报表获取失败: {str(e)}\n")

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取业绩预告时发生错误: {str(e)}\n{traceback.format_exc()}"


# ============================================================================
# 阶段 2：新闻数据获取
# ============================================================================

def get_china_stock_news(stock_code: str, curr_date: str = None) -> str:
    """
    获取中国A股个股新闻（含情感分析和风险预警）

    Args:
        stock_code: 股票代码
        curr_date: 当前日期（可选）

    Returns:
        str: 格式化的新闻数据，包含舆情统计和风险预警
    """
    try:
        result_parts = []
        result_parts.append(f"# {stock_code} 相关新闻\n")

        # 分级关键词体系
        positive_kw = ['预增', '增长', '突破', '新高', '买入评级', '中标', '签约', '扩产', '获批',
                       '业绩大增', '超预期', '利好', '创新高', '回购', '增持']
        negative_kw = ['预减', '亏损', '立案', '警示', '新低', '无法', '违规', '减持', '下调',
                       '业绩下滑', '不及预期', '利空', '下跌', '质押']

        # 风险关键词（高权重，需要高亮）
        risk_kw = ['立案调查', '退市', 'ST', '*ST', '警示函', '强制执行', '资不抵债',
                   '暂停上市', '终止上市', '欺诈发行', '财务造假', '重大违法']

        positive_count = 0
        negative_count = 0
        neutral_count = 0
        risk_found = []
        news_list = []

        # 获取东方财富个股新闻
        try:
            df_news = ak.stock_news_em(symbol=stock_code)
            if df_news is not None and not df_news.empty:
                # 取最近20条新闻
                df_recent = df_news.head(20)

                for idx, row in df_recent.iterrows():
                    title = str(row.get('新闻标题', row.get('标题', '')))
                    content = str(row.get('新闻内容', row.get('内容', '')))
                    pub_time = row.get('发布时间', row.get('时间', ''))

                    text = title + content

                    # 检测风险关键词
                    for kw in risk_kw:
                        if kw in text:
                            risk_found.append(kw)

                    # 普通情感判断
                    is_positive = any(kw in text for kw in positive_kw)
                    is_negative = any(kw in text for kw in negative_kw)

                    if is_positive and not is_negative:
                        sentiment = "正面"
                        positive_count += 1
                    elif is_negative and not is_positive:
                        sentiment = "负面"
                        negative_count += 1
                    else:
                        sentiment = "中性"
                        neutral_count += 1

                    news_list.append({
                        'title': title[:60] + '...' if len(title) > 60 else title,
                        'time': pub_time,
                        'sentiment': sentiment,
                        'content': content[:150] + '...' if len(content) > 150 else content
                    })

                # 输出舆情统计
                result_parts.append("## 舆情统计\n")

                # 风险预警（优先显示）
                if risk_found:
                    unique_risks = list(set(risk_found))
                    result_parts.append(f"⚠️ **重大风险预警**: 监测到 {', '.join(unique_risks)}\n")

                total = positive_count + negative_count + neutral_count
                if total > 0:
                    result_parts.append(f"- 新闻总数: {total}条")
                    result_parts.append(f"- 正面新闻: {positive_count}条 ({positive_count/total*100:.1f}%)")
                    result_parts.append(f"- 负面新闻: {negative_count}条 ({negative_count/total*100:.1f}%)")
                    result_parts.append(f"- 中性新闻: {neutral_count}条 ({neutral_count/total*100:.1f}%)")

                    # 舆情倾向判断
                    if positive_count > negative_count * 2:
                        result_parts.append(f"- **舆情倾向**: 积极\n")
                    elif negative_count > positive_count * 2:
                        result_parts.append(f"- **舆情倾向**: 消极\n")
                    else:
                        result_parts.append(f"- **舆情倾向**: 中性\n")

                # 新闻列表
                result_parts.append("## 最新新闻动态\n")
                result_parts.append("| 时间 | 标题 | 情感 |")
                result_parts.append("|------|------|------|")

                for news in news_list[:10]:
                    result_parts.append(f"| {news['time']} | {news['title']} | {news['sentiment']} |")

                if len(news_list) > 10:
                    result_parts.append(f"\n*（仅显示前10条，共{len(news_list)}条新闻）*\n")

                # 详细内容（前5条）
                result_parts.append("\n## 新闻详情（前5条）\n")
                for news in news_list[:5]:
                    result_parts.append(f"### {news['title']}")
                    result_parts.append(f"**发布时间**: {news['time']} | **情感**: {news['sentiment']}")
                    result_parts.append(f"{news['content']}\n")

            else:
                result_parts.append("暂无该股票的新闻数据\n")
        except Exception as e:
            result_parts.append(f"个股新闻获取失败: {str(e)}\n")

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取个股新闻时发生错误: {str(e)}\n{traceback.format_exc()}"


def get_china_market_news(curr_date: str = None) -> str:
    """
    获取中国财经市场新闻

    优先使用 Tushare，失败时 fallback 到 akshare

    Args:
        curr_date: 当前日期（可选）

    Returns:
        str: 格式化的市场新闻
    """
    # 优先尝试 Tushare
    try:
        from tradingagents.dataflows.tushare_utils import get_china_market_news_tushare
        tushare_result = get_china_market_news_tushare(curr_date)
        # 检查 Tushare 是否返回了有效内容（不仅仅是标题）
        if tushare_result and "[数据获取失败]" not in tushare_result:
            # 检查是否有实质性内容（不只是"暂不可用"的提示）
            if "暂不可用" not in tushare_result and len(tushare_result) > 200:
                return tushare_result
    except Exception as e:
        pass  # Tushare 失败，使用 akshare fallback

    # Akshare fallback
    try:
        result_parts = []
        result_parts.append("# 中国财经市场新闻 (akshare)\n")

        # 获取财联社快讯（使用 stock_info_global_cls 替代已废弃的 stock_zh_a_alerts_cls）
        try:
            df_cls = ak.stock_info_global_cls()
            if df_cls is not None and not df_cls.empty:
                result_parts.append("## 财联社快讯（最新20条）\n")
                df_recent = df_cls.head(20)

                for idx, row in df_recent.iterrows():
                    title = row.get('标题', '')
                    content = row.get('内容', '')
                    # 截断过长内容
                    if len(str(content)) > 300:
                        content = content[:300] + '...'
                    pub_date = row.get('发布日期', '')
                    pub_time = row.get('发布时间', '')
                    time_str = f"{pub_date} {pub_time}" if pub_date else pub_time

                    if title:
                        result_parts.append(f"**[{time_str}]** {title}")
                    if content:
                        result_parts.append(f"  {content}")
                    result_parts.append("")

                result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"财联社快讯获取失败: {str(e)}\n")

        # 获取央视新闻联播文字稿（经济相关）
        try:
            df_cctv = ak.news_cctv(date=datetime.now().strftime("%Y%m%d"))
            if df_cctv is not None and not df_cctv.empty:
                result_parts.append("## 央视新闻联播要点\n")
                # 筛选经济相关新闻
                economic_keywords = ['经济', '金融', '股市', '投资', '贸易', '产业', '制造', '科技']

                for idx, row in df_cctv.iterrows():
                    title = row.get('title', '')
                    if any(kw in title for kw in economic_keywords):
                        result_parts.append(f"- {title}")

                result_parts.append("\n")
        except Exception as e:
            # 央视新闻API可能不稳定，不报错
            pass

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取市场新闻时发生错误: {str(e)}\n{traceback.format_exc()}"


# ============================================================================
# 阶段 3：情绪数据获取
# ============================================================================

def get_china_stock_sentiment(stock_code: str) -> str:
    """
    获取中国A股情绪数据（千股千评、热度排名）

    Args:
        stock_code: 股票代码

    Returns:
        str: 格式化的情绪数据
    """
    try:
        result_parts = []
        result_parts.append(f"# {stock_code} 市场情绪分析\n")

        # 获取千股千评（注意：此API可能不稳定）
        try:
            df_comment = ak.stock_comment_em()
            if df_comment is not None and not df_comment.empty:
                # 尝试多种可能的列名
                code_col = None
                for col in ['代码', '股票代码', 'code']:
                    if col in df_comment.columns:
                        code_col = col
                        break

                if code_col:
                    stock_comment = df_comment[df_comment[code_col] == stock_code]
                    if not stock_comment.empty:
                        result_parts.append("## 千股千评\n")
                        result_parts.append(stock_comment.to_markdown(index=False))
                        result_parts.append("\n")
                    else:
                        result_parts.append("## 千股千评\n该股票暂无千股千评数据\n")
        except Exception as e:
            result_parts.append(f"## 千股千评\n数据获取失败（接口可能暂时不可用）\n")

        # 获取人气排名（此API较稳定）
        try:
            df_hot = ak.stock_hot_rank_em()
            if df_hot is not None and not df_hot.empty:
                # 查找目标股票在热度排名中的位置
                code_col = '代码' if '代码' in df_hot.columns else '股票代码'
                stock_hot = df_hot[df_hot[code_col] == stock_code]
                if not stock_hot.empty:
                    result_parts.append("## 人气热度排名\n")
                    result_parts.append(stock_hot.to_markdown(index=False))
                    result_parts.append("\n")
                else:
                    # 显示热度排名前10作为参考
                    result_parts.append("## 当前市场热度排名前10\n")
                    result_parts.append(df_hot.head(10).to_markdown(index=False))
                    result_parts.append(f"\n注：{stock_code} 未进入热度排名前100\n")
        except Exception as e:
            result_parts.append(f"人气排名获取失败: {str(e)}\n")

        # 获取股票热门关键词（此API可能不稳定）
        try:
            df_keywords = ak.stock_hot_keyword_em(symbol=stock_code)
            if df_keywords is not None and not df_keywords.empty:
                result_parts.append("## 热门关键词\n")
                result_parts.append(df_keywords.head(10).to_markdown(index=False))
                result_parts.append("\n")
        except Exception:
            # 关键词API不稳定，静默处理
            result_parts.append("## 热门关键词\n暂无数据\n")

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取情绪数据时发生错误: {str(e)}\n{traceback.format_exc()}"


def get_china_money_flow(stock_code: str) -> str:
    """
    获取中国A股资金流向（主力/散户/北向）

    Args:
        stock_code: 股票代码

    Returns:
        str: 格式化的资金流向数据
    """
    try:
        result_parts = []
        result_parts.append(f"# {stock_code} 资金流向分析\n")

        # 获取个股资金流向
        try:
            df_flow = ak.stock_individual_fund_flow(stock=stock_code, market="sh" if stock_code.startswith('6') else "sz")
            if df_flow is not None and not df_flow.empty:
                result_parts.append("## 近期资金流向\n")
                result_parts.append(df_flow.head(10).to_markdown(index=False))
                result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"个股资金流向获取失败: {str(e)}\n")

        # 获取个股资金流向排名
        try:
            df_rank = ak.stock_individual_fund_flow_rank(indicator="今日")
            if df_rank is not None and not df_rank.empty:
                stock_rank = df_rank[df_rank['代码'] == stock_code]
                if not stock_rank.empty:
                    result_parts.append("## 今日资金流向排名\n")
                    result_parts.append(stock_rank.to_markdown(index=False))
                    result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"资金流向排名获取失败: {str(e)}\n")

        # 获取北向资金数据
        try:
            df_north = ak.stock_hsgt_north_net_flow_in_em(symbol="北向")
            if df_north is not None and not df_north.empty:
                result_parts.append("## 北向资金近期流向\n")
                result_parts.append(df_north.tail(10).to_markdown(index=False))
                result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"北向资金数据获取失败: {str(e)}\n")

        # 获取北向资金持股明细
        try:
            df_north_hold = ak.stock_hsgt_hold_stock_em(market="北向", indicator="今日排行")
            if df_north_hold is not None and not df_north_hold.empty:
                stock_north = df_north_hold[df_north_hold['代码'] == stock_code]
                if not stock_north.empty:
                    result_parts.append("## 北向资金持股情况\n")
                    result_parts.append(stock_north.to_markdown(index=False))
                    result_parts.append("\n")
        except Exception as e:
            pass  # 北向持股API可能不稳定

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取资金流向时发生错误: {str(e)}\n{traceback.format_exc()}"


# ============================================================================
# 阶段 4：北向资金数据获取 (替代 Tushare 已停更的接口)
# ============================================================================

def get_hsgt_flow() -> str:
    """
    获取北向资金持股排行数据

    注意：2024年8月19日起，北向资金整体流向数据已停止披露，
    本函数仅返回仍可用的持股排行数据。

    Returns:
        str: 格式化的北向资金持股排行数据
    """
    try:
        result_parts = []
        result_parts.append("# 北向资金持股排行\n")
        result_parts.append("⚠️ 注：北向资金整体流向（每日净流入/流出）已于2024年8月停止披露，以下为仍可用的持股排行数据。\n\n")

        # 获取北向资金持股排行
        try:
            df_hold = ak.stock_hsgt_hold_stock_em(market="北向", indicator="今日排行")
            if df_hold is not None and not df_hold.empty:
                # 关键：提取实际数据日期，避免时间线穿帮
                actual_date = "未知"
                date_warning = ""
                if '日期' in df_hold.columns:
                    actual_date = str(df_hold['日期'].iloc[0])
                    # 计算数据年龄
                    try:
                        from datetime import datetime
                        data_date = datetime.strptime(actual_date, "%Y-%m-%d")
                        age_days = (datetime.now() - data_date).days
                        if age_days > 30:
                            date_warning = f"⚠️ **时效性警告**：数据日期为 {actual_date}，距今 {age_days} 天，请核实数据是否适用于当前分析。\n\n"
                        elif age_days > 7:
                            date_warning = f"📅 数据日期：{actual_date}（{age_days}天前，请注意时效性）\n\n"
                        elif age_days > 1:
                            date_warning = f"📅 数据日期：{actual_date}（{age_days}天前）\n\n"
                        else:
                            date_warning = f"📅 数据日期：{actual_date}\n\n"
                    except:
                        date_warning = f"📅 数据日期：{actual_date}\n\n"

                result_parts.append(f"## 持股市值前15（{actual_date}）\n")
                result_parts.append(date_warning)
                # 取前15名
                df_top = df_hold.head(15)
                cols = ['代码', '名称', '今日收盘价', '今日持股-市值', '今日增持估计-市值', '今日持股-占流通股比']
                available_cols = [c for c in cols if c in df_top.columns]
                result_parts.append(df_top[available_cols].to_markdown(index=False))
                result_parts.append("\n")

                # 计算整体统计
                total_value = df_hold['今日持股-市值'].sum() if '今日持股-市值' in df_hold.columns else 0
                total_change = df_hold['今日增持估计-市值'].sum() if '今日增持估计-市值' in df_hold.columns else 0
                result_parts.append(f"\n**统计**: 北向资金总持股市值约 {total_value/10000:.2f} 亿元")
                if total_change != 0:
                    direction = "增持" if total_change > 0 else "减持"
                    result_parts.append(f"，{actual_date}估计{direction} {abs(total_change)/10000:.2f} 亿元")
                result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"北向持股排行获取失败: {str(e)}\n")

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取北向资金流向时发生错误: {str(e)}\n{traceback.format_exc()}"


def get_hsgt_top10(trade_date: Optional[str] = None) -> str:
    """
    获取北向资金十大成交股/持股股

    Args:
        trade_date: 交易日期 YYYYMMDD（暂不使用，API返回最新数据）

    Returns:
        str: 格式化的北向资金十大持股数据
    """
    try:
        result_parts = []
        result_parts.append("# 北向资金十大持股 (AKShare)\n")

        # 获取北向资金持股排行
        try:
            df = ak.stock_hsgt_hold_stock_em(market="北向", indicator="今日排行")
            if df is not None and not df.empty:
                result_parts.append("## 北向资金持股市值前10\n")
                df_top10 = df.head(10)
                cols = ['代码', '名称', '今日收盘价', '今日涨跌幅', '今日持股-市值',
                       '今日持股-占流通股比', '今日增持估计-市值', '所属板块', '日期']
                available_cols = [c for c in cols if c in df_top10.columns]
                result_parts.append(df_top10[available_cols].to_markdown(index=False))
                result_parts.append("\n")

                # 数据日期
                if '日期' in df.columns:
                    result_parts.append(f"\n数据日期: {df['日期'].iloc[0]}\n")
        except Exception as e:
            result_parts.append(f"北向持股排行获取失败: {str(e)}\n")

        # 获取今日增持排行
        try:
            df_all = ak.stock_hsgt_hold_stock_em(market="北向", indicator="今日排行")
            if df_all is not None and not df_all.empty and '今日增持估计-市值' in df_all.columns:
                # 按增持金额排序
                df_sorted = df_all.sort_values('今日增持估计-市值', ascending=False)
                df_increase = df_sorted.head(10)
                result_parts.append("\n## 今日北向资金增持前10\n")
                cols = ['代码', '名称', '今日收盘价', '今日增持估计-市值', '今日增持估计-占流通股比']
                available_cols = [c for c in cols if c in df_increase.columns]
                result_parts.append(df_increase[available_cols].to_markdown(index=False))
                result_parts.append("\n")

                # 减持前10
                df_decrease = df_sorted.tail(10).iloc[::-1]
                result_parts.append("\n## 今日北向资金减持前10\n")
                result_parts.append(df_decrease[available_cols].to_markdown(index=False))
                result_parts.append("\n")
        except Exception as e:
            result_parts.append(f"增减持排行获取失败: {str(e)}\n")

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取北向资金十大持股时发生错误: {str(e)}\n{traceback.format_exc()}"


def get_hsgt_individual(stock_code: str) -> str:
    """
    获取个股北向资金持股历史

    ⚠️ 警告：此接口数据已于2024年8月停更，仅返回历史数据。
    外资态度分析请优先使用 get_top10_holders() 查看香港中央结算持股比例。

    Args:
        stock_code: 股票代码，如 "600036"

    Returns:
        str: 格式化的个股北向资金持股数据（历史数据，已停更）
    """
    try:
        from datetime import datetime
        result_parts = []
        result_parts.append(f"# {stock_code} 北向资金持股（⚠️ 数据已停更）\n")
        result_parts.append("**注意**：此数据源已于2024年8月停更，以下为历史数据。\n")
        result_parts.append("**推荐**：请使用 get_top10_holders 查看香港中央结算持股比例（季度数据）。\n\n")

        # 获取个股北向持股历史
        try:
            df = ak.stock_hsgt_individual_em(symbol=stock_code)
            if df is not None and not df.empty:
                # 取最近30条
                df_recent = df.tail(30)

                # 验证数据日期
                if '持股日期' in df_recent.columns:
                    latest_date_str = str(df_recent['持股日期'].iloc[-1])
                    try:
                        latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
                        age_days = (datetime.now() - latest_date).days
                        if age_days > 30:
                            result_parts.append(f"⚠️ **时效性警告**：数据截止于 {latest_date_str}，距今 {age_days} 天\n\n")
                        elif age_days > 7:
                            result_parts.append(f"📅 数据日期：{latest_date_str}（{age_days}天前）\n\n")
                        else:
                            result_parts.append(f"📅 数据日期：{latest_date_str}\n\n")
                    except:
                        result_parts.append(f"📅 数据日期：{latest_date_str}\n\n")

                # 外资态度摘要（方案A核心输出）
                if '持股数量' in df_recent.columns and '今日增持股数' in df_recent.columns:
                    latest = df_recent.iloc[-1]
                    prev = df_recent.iloc[-2] if len(df_recent) >= 2 else latest

                    latest_shares = latest['持股数量']
                    prev_shares = prev['持股数量']
                    change_shares = latest_shares - prev_shares

                    result_parts.append("## 外资态度摘要\n")
                    if change_shares > 0:
                        result_parts.append(f"📈 **外资加仓**：持股从 {prev_shares/10000:.0f}万股 增至 {latest_shares/10000:.0f}万股（+{change_shares/10000:.0f}万股）\n\n")
                    elif change_shares < 0:
                        result_parts.append(f"📉 **外资减仓**：持股从 {prev_shares/10000:.0f}万股 降至 {latest_shares/10000:.0f}万股（{change_shares/10000:.0f}万股）\n\n")
                    else:
                        result_parts.append(f"➡️ **外资持平**：持股维持在 {latest_shares/10000:.0f}万股\n\n")

                    # 近5日趋势
                    recent_5d = df_recent.tail(5)
                    if '今日增持资金' in recent_5d.columns:
                        recent_change = recent_5d['今日增持资金'].sum()
                        if recent_change != 0:
                            direction = "净增持" if recent_change > 0 else "净减持"
                            result_parts.append(f"**近5日趋势**：{direction} {abs(recent_change)/100000000:.2f} 亿元\n\n")

                # 持股明细表（精简显示最近10条）
                result_parts.append("## 持股历史（近10日）\n")
                df_display = df_recent.tail(10)
                cols = ['持股日期', '持股数量', '持股市值', '持股数量占A股百分比', '今日增持股数']
                available_cols = [c for c in cols if c in df_display.columns]
                result_parts.append(df_display[available_cols].to_markdown(index=False))
                result_parts.append("\n")

                # 当前持仓统计
                if '持股市值' in df_recent.columns:
                    latest = df_recent.iloc[-1]
                    result_parts.append(f"\n**当前持仓**：市值 {latest['持股市值']/100000000:.2f} 亿元，占流通股 {latest.get('持股数量占A股百分比', 0):.2f}%\n")
            else:
                result_parts.append(f"⚠️ 该股票未被北向资金持有，请使用前十大股东数据（方案B）判断外资态度\n")
        except Exception as e:
            result_parts.append(f"个股北向持股获取失败: {str(e)}\n")

        # 在持股排行中查找该股票
        try:
            df_rank = ak.stock_hsgt_hold_stock_em(market="北向", indicator="今日排行")
            if df_rank is not None and not df_rank.empty:
                stock_row = df_rank[df_rank['代码'] == stock_code]
                if not stock_row.empty:
                    result_parts.append("\n## 今日持股排名\n")
                    rank = stock_row.index[0] + 1
                    result_parts.append(f"在北向资金持股排行中位列第 **{rank}** 名\n")
                    result_parts.append(stock_row.to_markdown(index=False))
                    result_parts.append("\n")
        except Exception:
            pass

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取个股北向资金持股时发生错误: {str(e)}\n{traceback.format_exc()}"


# ============================================================================
# 阶段 5：A股排行榜数据
# ============================================================================

def get_stock_rank(
    rank_type: str = "涨幅榜",
    period: str = "今日",
    market: str = "全部",
    top_n: int = 20
) -> str:
    """
    获取 A 股排行榜数据

    Args:
        rank_type: 排行类型 - "涨幅榜", "跌幅榜", "成交额榜", "换手率榜", "资金流入榜", "资金流出榜"
        period: 时间周期 - "今日", "5日", "10日", "20日"
        market: 市场范围 - "全部", "沪市", "深市", "创业板", "科创板"
        top_n: 返回前N名，默认20

    Returns:
        str: 格式化的排行榜数据
    """
    logger.info(f"[get_stock_rank] 开始: rank_type={rank_type}, period={period}, market={market}, top_n={top_n}")
    print(f"[DEBUG] get_stock_rank 被调用: rank_type={rank_type}")  # 强制打印到控制台
    try:
        result_parts = []
        result_parts.append(f"# A股{rank_type} ({period})\n")

        # 优先使用 tushare（快速），回退到 akshare（慢）
        try:
            print("[DEBUG] 尝试导入 tushare...")
            from tradingagents.dataflows.tushare_utils import get_all_stocks_daily
            print("[DEBUG] 导入成功，调用 get_all_stocks_daily()...")
            df = get_all_stocks_daily()
            print(f"[DEBUG] tushare 返回: {len(df) if df is not None else 0} 行")
            if df is not None and not df.empty:
                logger.info(f"[get_stock_rank] 使用 tushare 数据源: {len(df)} 只股票")
                print(f"[DEBUG] 使用 tushare 数据源: {len(df)} 只股票")
            else:
                raise ValueError("tushare 数据为空")
        except Exception as e:
            import traceback
            logger.warning(f"[get_stock_rank] tushare 获取失败，回退到 akshare: {e}")
            print(f"[DEBUG] tushare 失败: {e}")
            print(f"[DEBUG] 异常详情:\n{traceback.format_exc()}")
            df = get_cached_stock_data()

        if df is None or df.empty:
            return "获取A股行情数据失败"

        # 市场筛选
        if market == "沪市":
            df = df[df['代码'].str.startswith('6')]
        elif market == "深市":
            df = df[df['代码'].str.startswith(('0', '3'))]
        elif market == "创业板":
            df = df[df['代码'].str.startswith('3')]
        elif market == "科创板":
            df = df[df['代码'].str.startswith('68')]

        # 排除 ST 股票
        df = df[~df['名称'].str.contains('ST|退', na=False)]

        # 根据排行类型排序
        if rank_type == "涨幅榜":
            if period == "今日":
                sort_col = '涨跌幅'
            elif period == "5日":
                sort_col = '5日涨跌幅' if '5日涨跌幅' in df.columns else '涨跌幅'
            elif period == "10日":
                sort_col = '10日涨跌幅' if '10日涨跌幅' in df.columns else '涨跌幅'
            else:
                sort_col = '涨跌幅'
            df_sorted = df.nlargest(top_n, sort_col)
            display_cols = ['代码', '名称', sort_col, '最新价', '成交额', '换手率']

        elif rank_type == "跌幅榜":
            sort_col = '涨跌幅'
            df_sorted = df.nsmallest(top_n, sort_col)
            display_cols = ['代码', '名称', '涨跌幅', '最新价', '成交额', '换手率']

        elif rank_type == "成交额榜":
            df_sorted = df.nlargest(top_n, '成交额')
            display_cols = ['代码', '名称', '成交额', '涨跌幅', '最新价', '换手率']

        elif rank_type == "换手率榜":
            df_sorted = df.nlargest(top_n, '换手率')
            display_cols = ['代码', '名称', '换手率', '涨跌幅', '最新价', '成交额']

        elif rank_type in ["资金流入榜", "资金流出榜"]:
            # 使用资金流向排名 API（注意：此 API 较慢，需要分页请求）
            logger.warning(f"[诊断] 即将调用慢速 API: ak.stock_individual_fund_flow_rank(indicator={period})")
            try:
                indicator = "今日" if period == "今日" else period.replace("日", "日")
                df_flow = ak.stock_individual_fund_flow_rank(indicator=indicator)
                if df_flow is not None and not df_flow.empty:
                    if rank_type == "资金流入榜":
                        df_sorted = df_flow.nlargest(top_n, '主力净流入-净额')
                    else:
                        df_sorted = df_flow.nsmallest(top_n, '主力净流入-净额')
                    display_cols = ['代码', '名称', '最新价', '涨跌幅', '主力净流入-净额', '主力净流入-净占比']
                    result_parts.append(f"市场范围: {market}\n")
                    result_parts.append(f"返回数量: 前{top_n}名\n\n")

                    # 格式化金额显示
                    if '主力净流入-净额' in df_sorted.columns:
                        df_sorted = df_sorted.copy()
                        df_sorted['主力净流入-净额'] = df_sorted['主力净流入-净额'].apply(
                            lambda x: f"{x/100000000:.2f}亿" if abs(x) >= 100000000 else f"{x/10000:.0f}万"
                        )

                    available_cols = [c for c in display_cols if c in df_sorted.columns]
                    result_parts.append(df_sorted[available_cols].to_markdown(index=False))
                    return "\n".join(result_parts)
            except Exception as e:
                return f"获取资金流向排行失败: {str(e)}"

        else:
            return f"不支持的排行类型: {rank_type}"

        result_parts.append(f"市场: {market} | 前{top_n}名\n")

        # 紧凑格式输出（避免 markdown 表格占用太多 tokens）
        for idx, row in df_sorted.head(top_n).iterrows():
            code = row.get('代码', '')
            name = row.get('名称', '')
            price = row.get('最新价', 0)
            change = row.get('涨跌幅', row.get(sort_col, 0)) if 'sort_col' in dir() else row.get('涨跌幅', 0)
            amount = row.get('成交额', 0)
            turnover = row.get('换手率', 0)

            # 格式化金额
            amount_str = f"{amount/100000000:.1f}亿" if amount >= 100000000 else f"{amount/10000:.0f}万"
            change_str = f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"

            result_parts.append(f"{code} {name} {change_str} ¥{price:.2f} 成交{amount_str}")

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取排行榜数据时发生错误: {str(e)}\n{traceback.format_exc()}"


def get_continuous_up_stocks(days: int = 3, top_n: int = 20) -> str:
    """
    获取连续上涨股票

    Args:
        days: 连涨天数，默认3天
        top_n: 返回前N名

    Returns:
        str: 格式化的连续上涨股票列表
    """
    try:
        result_parts = []
        result_parts.append(f"# 连续上涨{days}天以上的股票\n")

        # 使用同花顺连续上涨榜
        df = ak.stock_rank_ljqd_ths()
        if df is None or df.empty:
            return "获取连续上涨数据失败"

        # 筛选连涨天数
        if '连涨天数' in df.columns:
            df = df[df['连涨天数'] >= days]

        df_top = df.head(top_n)
        result_parts.append(f"共{len(df_top)}只\n")

        # 紧凑格式输出
        for _, row in df_top.iterrows():
            code = row.get('代码', '')
            name = row.get('名称', '')
            price = row.get('最新价', 0)
            days_up = row.get('连涨天数', 0)
            total_change = row.get('累计涨幅', 0)
            result_parts.append(f"{code} {name} 连涨{days_up}天 累计+{total_change:.1f}% ¥{price:.2f}")

        return "\n".join(result_parts)

    except Exception as e:
        return f"获取连续上涨股票时发生错误: {str(e)}\n{traceback.format_exc()}"


def get_hot_stocks(top_n: int = 20) -> str:
    """
    获取热门股票（基于人气榜/关注度）

    Args:
        top_n: 返回前N名

    Returns:
        str: 格式化的热门股票列表
    """
    try:
        result_parts = []
        result_parts.append(f"# 热门股票 (前{top_n})\n")

        # 优先使用 tushare（快速），回退到 akshare（慢）
        try:
            from tradingagents.dataflows.tushare_utils import get_all_stocks_daily
            df = get_all_stocks_daily()
            if df is None or df.empty:
                raise ValueError("tushare 数据为空")
            logger.info(f"[get_hot_stocks] 使用 tushare: {len(df)} 只股票")
        except Exception as e:
            logger.warning(f"[get_hot_stocks] tushare 失败，回退到 akshare: {e}")
            df = get_cached_stock_data()
        if df is not None and not df.empty:
            df = df[~df['名称'].str.contains('ST|退', na=False)]
            df_top = df.nlargest(top_n, '成交额')
            for _, row in df_top.iterrows():
                code = row.get('代码', '')
                name = row.get('名称', '')
                price = row.get('最新价', 0)
                change = row.get('涨跌幅', 0)
                amount = row.get('成交额', 0)
                amount_str = f"{amount/100000000:.1f}亿"
                change_str = f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"
                result_parts.append(f"{code} {name} {change_str} ¥{price:.2f} 成交{amount_str}")
            return "\n".join(result_parts)

        # 回退到人气榜 API（较慢）
        try:
            df = ak.stock_rank_xstp_ths()
            if df is not None and not df.empty:
                df_top = df.head(top_n)
                for _, row in df_top.iterrows():
                    # 使用正确的列名
                    code = row.get('股票代码', row.get('代码', ''))
                    name = row.get('股票简称', row.get('名称', ''))
                    price = row.get('最新价', 0)
                    change = row.get('涨跌幅', 0)
                    change_str = f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"
                    result_parts.append(f"{code} {name} {change_str} ¥{price:.2f}")
                return "\n".join(result_parts)
        except Exception:
            pass

        return "获取热门股票数据失败"

    except Exception as e:
        return f"获取热门股票时发生错误: {str(e)}\n{traceback.format_exc()}"


# ============================================================================
# 板块数据
# ============================================================================

def get_sector_ranking(indicator: str = "行业", top_n: int = 15) -> str:
    """
    获取板块涨跌幅排行

    Args:
        indicator: 板块类型，可选 "行业" / "概念" / "地域"
        top_n: 返回前N个板块

    Returns:
        str: 格式化的板块排行数据
    """
    import akshare as ak

    try:
        # 获取板块实时行情
        df = ak.stock_sector_spot(indicator=indicator)

        if df is None or df.empty:
            return f"暂无{indicator}板块数据"

        # 按涨跌幅排序
        df = df.sort_values('涨跌幅', ascending=False)

        result = [f"# {indicator}板块涨跌幅排行\n\n"]
        result.append(f"共 {len(df)} 个板块\n\n")

        # 领涨板块
        result.append("## 领涨板块\n\n")
        for i, (_, row) in enumerate(df.head(top_n).iterrows(), 1):
            sector_name = row.get('板块', 'N/A')
            change_pct = row.get('涨跌幅', 0)
            volume = row.get('总成交额', 0)
            volume_str = f"{volume/1e8:.1f}亿" if volume > 0 else "N/A"
            result.append(f"{i}. **{sector_name}** {change_pct:+.2f}% 成交{volume_str}\n")

        # 领跌板块
        result.append("\n## 领跌板块\n\n")
        for i, (_, row) in enumerate(df.tail(5).iloc[::-1].iterrows(), 1):
            sector_name = row.get('板块', 'N/A')
            change_pct = row.get('涨跌幅', 0)
            result.append(f"{i}. **{sector_name}** {change_pct:+.2f}%\n")

        return "".join(result)

    except Exception as e:
        logger.error(f"获取{indicator}板块数据失败: {e}")
        return f"获取{indicator}板块数据失败: {str(e)}"


# ============================================================================
# 工具函数
# ============================================================================

# is_china_stock 函数已移至 tradingagents.agents.utils.agent_utils
# 为保持向后兼容，此处重新导出
from tradingagents.agents.utils.agent_utils import is_china_stock


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("测试 akshare_utils.py")
    print("=" * 60)

    test_stock = "601899"  # 紫金矿业

    print(f"\n测试股票: {test_stock}")
    print("-" * 40)

    print("\n1. 测试财务报表获取...")
    result = get_financial_report(test_stock, "all")
    print(result[:1000] + "..." if len(result) > 1000 else result)

    print("\n2. 测试核心指标获取...")
    result = get_stock_indicators(test_stock)
    print(result[:1000] + "..." if len(result) > 1000 else result)

    print("\n3. 测试业绩预告获取...")
    result = get_earnings_forecast(test_stock)
    print(result[:1000] + "..." if len(result) > 1000 else result)

    print("\n4. 测试个股新闻获取...")
    result = get_china_stock_news(test_stock)
    print(result[:1000] + "..." if len(result) > 1000 else result)

    print("\n5. 测试情绪数据获取...")
    result = get_china_stock_sentiment(test_stock)
    print(result[:1000] + "..." if len(result) > 1000 else result)

    print("\n6. 测试资金流向获取...")
    result = get_china_money_flow(test_stock)
    print(result[:1000] + "..." if len(result) > 1000 else result)
