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
    获取中国A股个股新闻

    Args:
        stock_code: 股票代码
        curr_date: 当前日期（可选）

    Returns:
        str: 格式化的新闻数据
    """
    try:
        result_parts = []
        result_parts.append(f"# {stock_code} 相关新闻\n")

        # 获取东方财富个股新闻
        try:
            df_news = ak.stock_news_em(symbol=stock_code)
            if df_news is not None and not df_news.empty:
                result_parts.append("## 最新新闻动态\n")
                # 取最近20条新闻
                df_recent = df_news.head(20)

                for idx, row in df_recent.iterrows():
                    title = row.get('新闻标题', row.get('标题', ''))
                    content = row.get('新闻内容', row.get('内容', ''))[:200] + '...' if len(str(row.get('新闻内容', row.get('内容', '')))) > 200 else row.get('新闻内容', row.get('内容', ''))
                    pub_time = row.get('发布时间', row.get('时间', ''))

                    result_parts.append(f"### {title}")
                    result_parts.append(f"**发布时间**: {pub_time}")
                    result_parts.append(f"{content}\n")

                result_parts.append("\n")
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

    Args:
        curr_date: 当前日期（可选）

    Returns:
        str: 格式化的市场新闻
    """
    try:
        result_parts = []
        result_parts.append("# 中国财经市场新闻\n")

        # 获取财联社快讯
        try:
            df_cls = ak.stock_zh_a_alerts_cls()
            if df_cls is not None and not df_cls.empty:
                result_parts.append("## 财联社快讯（最新20条）\n")
                df_recent = df_cls.head(20)

                for idx, row in df_recent.iterrows():
                    title = row.get('标题', '')
                    content = row.get('内容', '')[:300] if len(str(row.get('内容', ''))) > 300 else row.get('内容', '')
                    pub_time = row.get('发布时间', row.get('时间', ''))

                    result_parts.append(f"**[{pub_time}]** {title}")
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
# 工具函数
# ============================================================================

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
