"""
Tushare Pro 数据获取模块

提供中国A股数据获取功能，包括：
- 财务报表（利润表、资产负债表、现金流量表）
- 财务指标（ROE、ROA、毛利率等150+指标）
- 每日估值（PE、PB、市值、换手率）
- 业绩预告
- 股东数据
- 资金流向
- 宏观经济数据
"""

import os
import logging
from typing import Optional
from datetime import datetime, timedelta

import tushare as ts
import pandas as pd

from .retry_utils import (
    retry_with_backoff,
    safe_api_call,
    get_tushare_error_message,
    DataResponse,
    ErrorCategory
)

logger = logging.getLogger(__name__)


# 全局 pro API 实例
_pro_api = None


def get_tushare_token() -> str:
    """
    获取 Tushare Token，优先从环境变量读取，其次从配置文件读取
    """
    # 优先环境变量
    token = os.getenv("TUSHARE_TOKEN", "")
    if token:
        return token

    # 其次从配置文件读取
    try:
        from tradingagents.default_config import DEFAULT_CONFIG
        token = DEFAULT_CONFIG.get("tushare_token", "")
        if token:
            return token
    except ImportError:
        pass

    return ""


def get_pro_api():
    """获取 Tushare Pro API 实例"""
    global _pro_api
    if _pro_api is None:
        token = get_tushare_token()
        if not token:
            raise ValueError(
                "Tushare Token 未设置。请设置环境变量 TUSHARE_TOKEN 或在 default_config.py 中配置 tushare_token。\n"
                "获取Token: https://tushare.pro/register"
            )
        ts.set_token(token)
        _pro_api = ts.pro_api()
    return _pro_api


def convert_stock_code(stock_code: str) -> str:
    """
    将股票代码转换为 Tushare 格式

    Args:
        stock_code: 6位股票代码 (如 "601899") 或带后缀格式 (如 "601899.SH")

    Returns:
        Tushare 格式的股票代码 (如 "601899.SH")
    """
    # 移除可能的后缀
    clean_code = stock_code.split('.')[0]

    # 根据代码前缀确定交易所
    if clean_code.startswith(('6', '9')):  # 上海
        return f"{clean_code}.SH"
    elif clean_code.startswith(('0', '2', '3')):  # 深圳
        return f"{clean_code}.SZ"
    elif clean_code.startswith(('4', '8')):  # 北交所/新三板
        return f"{clean_code}.BJ"
    else:
        return f"{clean_code}.SH"  # 默认上海


@retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
def _fetch_stock_basic(ts_code: str):
    """内部函数：获取股票基本信息（带重试）"""
    pro = get_pro_api()
    return pro.stock_basic(
        ts_code=ts_code,
        fields='ts_code,symbol,name,area,industry,fullname,list_date,market'
    )


def get_stock_basic_info(stock_code: str) -> str:
    """
    获取股票基本信息

    Args:
        stock_code: 股票代码

    Returns:
        股票基本信息的格式化字符串
    """
    try:
        ts_code = convert_stock_code(stock_code)
        df = _fetch_stock_basic(ts_code)

        if df.empty:
            return f"[not_found] 未找到股票 {stock_code} 的基本信息。请确认代码正确且股票未退市。"

        row = df.iloc[0]
        return f"""
## 股票基本信息

- **代码**: {row.get('ts_code', 'N/A')}
- **名称**: {row.get('name', 'N/A')}
- **全称**: {row.get('fullname', 'N/A')}
- **行业**: {row.get('industry', 'N/A')}
- **地区**: {row.get('area', 'N/A')}
- **上市日期**: {row.get('list_date', 'N/A')}
- **市场**: {row.get('market', 'N/A')}
"""
    except Exception as e:
        logger.error(f"获取股票基本信息失败 [{stock_code}]: {e}")
        return get_tushare_error_message(stock_code, "股票基本信息", e)


def get_financial_statements(stock_code: str) -> str:
    """
    获取财务报表（利润表、资产负债表、现金流量表）

    Args:
        stock_code: 股票代码

    Returns:
        财务报表的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        result = []
        result.append("# 财务报表分析\n")

        # 获取利润表
        income_df = pro.income(ts_code=ts_code,
                              fields='ts_code,end_date,revenue,operate_profit,total_profit,n_income,basic_eps')
        if not income_df.empty:
            income_df = income_df.head(4)  # 最近4个季度
            result.append("## 利润表（最近4个季度）\n")
            result.append("| 报告期 | 营业收入(亿) | 营业利润(亿) | 利润总额(亿) | 净利润(亿) | 基本EPS |")
            result.append("|--------|------------|------------|------------|----------|---------|")
            for _, row in income_df.iterrows():
                revenue = row['revenue'] / 1e8 if pd.notna(row['revenue']) else 0
                op_profit = row['operate_profit'] / 1e8 if pd.notna(row['operate_profit']) else 0
                total_profit = row['total_profit'] / 1e8 if pd.notna(row['total_profit']) else 0
                n_income = row['n_income'] / 1e8 if pd.notna(row['n_income']) else 0
                eps = row['basic_eps'] if pd.notna(row['basic_eps']) else 0
                result.append(f"| {row['end_date']} | {revenue:.2f} | {op_profit:.2f} | {total_profit:.2f} | {n_income:.2f} | {eps:.3f} |")
            result.append("")

        # 获取资产负债表
        balance_df = pro.balancesheet(ts_code=ts_code,
                                      fields='ts_code,end_date,total_assets,total_liab,total_hldr_eqy_exc_min_int,money_cap')
        if not balance_df.empty:
            balance_df = balance_df.head(4)
            result.append("## 资产负债表（最近4个季度）\n")
            result.append("| 报告期 | 总资产(亿) | 总负债(亿) | 股东权益(亿) | 货币资金(亿) |")
            result.append("|--------|----------|----------|------------|------------|")
            for _, row in balance_df.iterrows():
                total_assets = row['total_assets'] / 1e8 if pd.notna(row['total_assets']) else 0
                total_liab = row['total_liab'] / 1e8 if pd.notna(row['total_liab']) else 0
                equity = row['total_hldr_eqy_exc_min_int'] / 1e8 if pd.notna(row['total_hldr_eqy_exc_min_int']) else 0
                cash = row['money_cap'] / 1e8 if pd.notna(row['money_cap']) else 0
                result.append(f"| {row['end_date']} | {total_assets:.2f} | {total_liab:.2f} | {equity:.2f} | {cash:.2f} |")
            result.append("")

        # 获取现金流量表
        cashflow_df = pro.cashflow(ts_code=ts_code,
                                   fields='ts_code,end_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,free_cashflow')
        if not cashflow_df.empty:
            cashflow_df = cashflow_df.head(4)
            result.append("## 现金流量表（最近4个季度）\n")
            result.append("| 报告期 | 经营现金流(亿) | 投资现金流(亿) | 筹资现金流(亿) | 自由现金流(亿) |")
            result.append("|--------|--------------|--------------|--------------|--------------|")
            for _, row in cashflow_df.iterrows():
                cf_op = row['n_cashflow_act'] / 1e8 if pd.notna(row['n_cashflow_act']) else 0
                cf_inv = row['n_cashflow_inv_act'] / 1e8 if pd.notna(row['n_cashflow_inv_act']) else 0
                cf_fin = row['n_cash_flows_fnc_act'] / 1e8 if pd.notna(row['n_cash_flows_fnc_act']) else 0
                fcf = row['free_cashflow'] / 1e8 if pd.notna(row['free_cashflow']) else 0
                result.append(f"| {row['end_date']} | {cf_op:.2f} | {cf_inv:.2f} | {cf_fin:.2f} | {fcf:.2f} |")
            result.append("")

        return "\n".join(result) if result else "未获取到财务报表数据"

    except Exception as e:
        return f"获取财务报表失败: {str(e)}"


def get_financial_indicators(stock_code: str) -> str:
    """
    获取财务指标（ROE、ROA、毛利率、净利率等）

    Args:
        stock_code: 股票代码

    Returns:
        财务指标的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        # 注意：gross_margin是毛利(金额)，grossprofit_margin才是销售毛利率(百分比)
        df = pro.fina_indicator(ts_code=ts_code,
                               fields='ts_code,end_date,eps,bps,roe,roa,grossprofit_margin,netprofit_margin,debt_to_assets,current_ratio,quick_ratio,netprofit_yoy,tr_yoy')

        if df.empty:
            return f"未找到股票 {stock_code} 的财务指标"

        df = df.head(4)  # 最近4个季度

        result = []
        result.append("# 财务指标分析\n")

        # 盈利能力
        result.append("## 盈利能力指标\n")
        result.append("| 报告期 | ROE(%) | ROA(%) | 毛利率(%) | 净利率(%) |")
        result.append("|--------|--------|--------|----------|----------|")
        for _, row in df.iterrows():
            roe = row['roe'] if pd.notna(row['roe']) else 0
            roa = row['roa'] if pd.notna(row['roa']) else 0
            # 使用 grossprofit_margin（销售毛利率%），而非 gross_margin（毛利金额）
            gm = row['grossprofit_margin'] if pd.notna(row['grossprofit_margin']) else 0
            npm = row['netprofit_margin'] if pd.notna(row['netprofit_margin']) else 0
            result.append(f"| {row['end_date']} | {roe:.2f} | {roa:.2f} | {gm:.2f} | {npm:.2f} |")
        result.append("")

        # 每股指标
        result.append("## 每股指标\n")
        result.append("| 报告期 | EPS(元) | BPS(元) |")
        result.append("|--------|---------|---------|")
        for _, row in df.iterrows():
            eps = row['eps'] if pd.notna(row['eps']) else 0
            bps = row['bps'] if pd.notna(row['bps']) else 0
            result.append(f"| {row['end_date']} | {eps:.3f} | {bps:.2f} |")
        result.append("")

        # 偿债能力
        result.append("## 偿债能力指标\n")
        result.append("| 报告期 | 资产负债率(%) | 流动比率 | 速动比率 |")
        result.append("|--------|--------------|---------|---------|")
        for _, row in df.iterrows():
            debt_ratio = row['debt_to_assets'] if pd.notna(row['debt_to_assets']) else 0
            current = row['current_ratio'] if pd.notna(row['current_ratio']) else 0
            quick = row['quick_ratio'] if pd.notna(row['quick_ratio']) else 0
            result.append(f"| {row['end_date']} | {debt_ratio:.2f} | {current:.2f} | {quick:.2f} |")
        result.append("")

        # 增长率
        result.append("## 增长率指标\n")
        result.append("| 报告期 | 净利润同比(%) | 营收同比(%) |")
        result.append("|--------|-------------|-----------|")
        for _, row in df.iterrows():
            np_yoy = row['netprofit_yoy'] if pd.notna(row['netprofit_yoy']) else 0
            tr_yoy = row['tr_yoy'] if pd.notna(row['tr_yoy']) else 0
            result.append(f"| {row['end_date']} | {np_yoy:.2f} | {tr_yoy:.2f} |")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取财务指标失败: {str(e)}"


def get_daily_basic(stock_code: str, trade_date: Optional[str] = None) -> str:
    """
    获取每日估值指标（PE、PB、市值、换手率等）

    Args:
        stock_code: 股票代码
        trade_date: 交易日期 (YYYYMMDD格式)，默认获取最近30天

    Returns:
        估值指标的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        if trade_date:
            df = pro.daily_basic(ts_code=ts_code, trade_date=trade_date,
                                fields='ts_code,trade_date,pe,pb,ps,total_mv,circ_mv,turnover_rate,volume_ratio')
        else:
            # 获取最近30天数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
            df = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date,
                                fields='ts_code,trade_date,pe,pb,ps,total_mv,circ_mv,turnover_rate,volume_ratio')

        if df.empty:
            return f"未找到股票 {stock_code} 的估值数据"

        df = df.head(10)  # 最近10天

        result = []
        result.append("# 估值指标分析\n")
        result.append("## 每日估值数据（最近10个交易日）\n")
        result.append("| 日期 | PE(TTM) | PB | PS | 总市值(亿) | 流通市值(亿) | 换手率(%) | 量比 |")
        result.append("|------|---------|-----|-----|-----------|------------|----------|------|")

        for _, row in df.iterrows():
            pe = row['pe'] if pd.notna(row['pe']) else 0
            pb = row['pb'] if pd.notna(row['pb']) else 0
            ps = row['ps'] if pd.notna(row['ps']) else 0
            total_mv = row['total_mv'] / 10000 if pd.notna(row['total_mv']) else 0  # 万元转亿元
            circ_mv = row['circ_mv'] / 10000 if pd.notna(row['circ_mv']) else 0
            turnover = row['turnover_rate'] if pd.notna(row['turnover_rate']) else 0
            volume_ratio = row['volume_ratio'] if pd.notna(row['volume_ratio']) else 0
            result.append(f"| {row['trade_date']} | {pe:.2f} | {pb:.2f} | {ps:.2f} | {total_mv:.2f} | {circ_mv:.2f} | {turnover:.2f} | {volume_ratio:.2f} |")

        # 计算平均值（安全处理 None/NaN）
        def safe_float(val, default=0.0):
            """安全转换为float，处理None和NaN"""
            if val is None or pd.isna(val):
                return default
            return float(val)

        result.append("")
        avg_pe = safe_float(df['pe'].mean(), 0)
        avg_pb = safe_float(df['pb'].mean(), 0)
        latest = df.iloc[0]
        latest_pe = safe_float(latest['pe'], 0)
        latest_pb = safe_float(latest['pb'], 0)

        if latest_pe > 0 or latest_pb > 0:
            result.append(f"**最新估值**: PE={latest_pe:.2f}, PB={latest_pb:.2f}")
            result.append(f"**近期平均**: PE={avg_pe:.2f}, PB={avg_pb:.2f}")
        else:
            result.append("**最新估值**: 数据暂不可用（该股可能为亏损股或数据源缺失）")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取估值数据失败: {str(e)}"


def get_forecast(stock_code: str) -> str:
    """
    获取业绩预告

    Args:
        stock_code: 股票代码

    Returns:
        业绩预告的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        df = pro.forecast(ts_code=ts_code)

        if df.empty:
            return f"股票 {stock_code} 暂无业绩预告"

        df = df.head(5)  # 最近5条

        result = []
        result.append("# 业绩预告\n")

        for _, row in df.iterrows():
            result.append(f"## {row['end_date']} 业绩预告\n")
            result.append(f"- **公告日期**: {row.get('ann_date', 'N/A')}")
            result.append(f"- **预告类型**: {row.get('type', 'N/A')}")
            result.append(f"- **业绩变动幅度**: {row.get('p_change_min', 0):.1f}% ~ {row.get('p_change_max', 0):.1f}%")

            net_min = row.get('net_profit_min', 0)
            net_max = row.get('net_profit_max', 0)
            if net_min and net_max:
                result.append(f"- **预计净利润**: {net_min/10000:.2f}亿 ~ {net_max/10000:.2f}亿")

            if row.get('summary'):
                result.append(f"- **预告摘要**: {row['summary'][:200]}...")

            if row.get('change_reason'):
                result.append(f"- **变动原因**: {row['change_reason'][:300]}...")

            result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取业绩预告失败: {str(e)}"


def get_top10_holders(stock_code: str) -> str:
    """
    获取前十大股东

    Args:
        stock_code: 股票代码

    Returns:
        前十大股东的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        # 获取最近两期数据进行对比
        df = pro.top10_holders(ts_code=ts_code)

        if df.empty:
            return f"未找到股票 {stock_code} 的股东数据"

        # 获取最新一期
        latest_date = df['end_date'].max()
        latest_df = df[df['end_date'] == latest_date].head(10)

        result = []
        result.append("# 前十大股东分析\n")
        result.append(f"## 截至 {latest_date} 前十大股东\n")
        result.append("| 排名 | 股东名称 | 持股数量(万股) | 持股比例(%) | 股东类型 |")
        result.append("|------|---------|--------------|------------|---------|")

        for i, (_, row) in enumerate(latest_df.iterrows(), 1):
            name = row['holder_name'][:20] if len(row['holder_name']) > 20 else row['holder_name']
            amount = row['hold_amount'] / 10000 if pd.notna(row['hold_amount']) else 0
            ratio = row['hold_ratio'] if pd.notna(row['hold_ratio']) else 0
            holder_type = row.get('holder_type', 'N/A')
            result.append(f"| {i} | {name} | {amount:.2f} | {ratio:.2f} | {holder_type} |")

        result.append("")

        # 计算机构持股比例
        total_ratio = latest_df['hold_ratio'].sum()
        result.append(f"**前十大股东合计持股**: {total_ratio:.2f}%")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取股东数据失败: {str(e)}"


def get_holder_number(stock_code: str) -> str:
    """
    获取股东人数变化趋势（筹码集中度）

    Args:
        stock_code: 股票代码

    Returns:
        股东人数的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        df = pro.stk_holdernumber(ts_code=ts_code)

        if df.empty:
            return f"未找到股票 {stock_code} 的股东人数数据"

        df = df.head(8)  # 最近8期

        result = []
        result.append("# 股东人数变化（筹码集中度）\n")
        result.append("| 报告期 | 股东人数 | 环比变化 |")
        result.append("|--------|---------|---------|")

        prev_num = None
        for _, row in df.iterrows():
            num = row['holder_num']
            if prev_num:
                change = (num - prev_num) / prev_num * 100
                change_str = f"{change:+.2f}%"
            else:
                change_str = "-"
            result.append(f"| {row['end_date']} | {num:,} | {change_str} |")
            prev_num = num

        result.append("")

        # 分析趋势
        latest = df.iloc[0]['holder_num']
        oldest = df.iloc[-1]['holder_num']
        total_change = (latest - oldest) / oldest * 100

        if total_change < -10:
            trend = "股东人数持续减少，筹码趋于集中，可能有主力吸筹"
        elif total_change > 10:
            trend = "股东人数持续增加，筹码趋于分散，可能有主力出货"
        else:
            trend = "股东人数相对稳定，筹码分布变化不大"

        result.append(f"**趋势分析**: {trend}")
        result.append(f"**期间变化**: {total_change:+.2f}%")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取股东人数数据失败: {str(e)}"


def get_moneyflow(stock_code: str, days: int = 10) -> str:
    """
    获取个股资金流向

    Args:
        stock_code: 股票代码
        days: 获取天数

    Returns:
        资金流向的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')

        df = pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df.empty:
            return f"未找到股票 {stock_code} 的资金流向数据"

        df = df.head(days)

        result = []
        result.append("# 资金流向分析\n")
        result.append("## 每日资金流向（单位：万元）\n")
        result.append("| 日期 | 大单净流入 | 中单净流入 | 小单净流入 | 净流入合计 |")
        result.append("|------|-----------|-----------|-----------|-----------|")

        for _, row in df.iterrows():
            # 计算各档净流入
            lg_net = (row.get('buy_lg_amount', 0) - row.get('sell_lg_amount', 0)) / 10000
            md_net = (row.get('buy_md_amount', 0) - row.get('sell_md_amount', 0)) / 10000
            sm_net = (row.get('buy_sm_amount', 0) - row.get('sell_sm_amount', 0)) / 10000
            total_net = row.get('net_mf_amount', 0) / 10000

            result.append(f"| {row['trade_date']} | {lg_net:+.2f} | {md_net:+.2f} | {sm_net:+.2f} | {total_net:+.2f} |")

        result.append("")

        # 汇总分析
        total_lg_net = sum((row.get('buy_lg_amount', 0) - row.get('sell_lg_amount', 0)) for _, row in df.iterrows()) / 10000
        total_net = df['net_mf_amount'].sum() / 10000

        result.append(f"**{days}日大单净流入合计**: {total_lg_net:+.2f}万元")
        result.append(f"**{days}日资金净流入合计**: {total_net:+.2f}万元")

        if total_net > 0:
            result.append("**资金面分析**: 近期资金持续流入，买盘力量较强")
        else:
            result.append("**资金面分析**: 近期资金持续流出，卖盘压力较大")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取资金流向数据失败: {str(e)}"


def get_hsgt_flow() -> str:
    """
    获取沪深港通资金流向（北向资金整体流向）

    ⚠️ 数据已停更说明：
    2024年8月19日起，沪深交所调整信息披露机制，北向资金整体流向数据已停止实时披露。
    此函数保留用于向后兼容，但不再返回有效数据。

    建议替代方案：
    - get_hsgt_top10(): 获取每日北向资金十大成交股（仍可用）
    - 前十大股东中的"香港中央结算"持股比例变化可作为参考

    Returns:
        说明信息
    """
    return """# 北向资金整体流向

**⚠️ 数据已停更**

2024年8月19日起，沪深交所调整信息披露机制，北向资金整体流向数据已停止实时披露。

**可用替代数据源：**
1. **北向十大成交股** (`hsgt_top10`)：查看每日北向资金最活跃的股票
2. **前十大股东**: 关注"香港中央结算"持股比例季度变化

请使用以上替代数据进行分析。

注：港交所自2024年8月20日起停止披露北向资金每日数据，个股持股明细(hk_hold)仅有季度快照。
"""


def get_margin_data(stock_code: str) -> str:
    """
    获取融资融券数据

    Args:
        stock_code: 股票代码

    Returns:
        融资融券数据的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

        df = pro.margin_detail(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df.empty:
            return f"未找到股票 {stock_code} 的融资融券数据"

        df = df.head(10)  # 最近10天

        result = []
        result.append("# 融资融券分析\n")
        result.append("## 最近10个交易日融资融券数据\n")
        result.append("| 日期 | 融资余额(亿) | 融资买入(亿) | 融券余额(万) | 融券卖出(万股) |")
        result.append("|------|------------|------------|------------|--------------|")

        for _, row in df.iterrows():
            rzye = row.get('rzye', 0) / 1e8 if pd.notna(row.get('rzye')) else 0
            rzmre = row.get('rzmre', 0) / 1e8 if pd.notna(row.get('rzmre')) else 0
            rqye = row.get('rqye', 0) / 1e4 if pd.notna(row.get('rqye')) else 0
            rqmcl = row.get('rqmcl', 0) / 1e4 if pd.notna(row.get('rqmcl')) else 0
            result.append(f"| {row['trade_date']} | {rzye:.2f} | {rzmre:.2f} | {rqye:.2f} | {rqmcl:.2f} |")

        result.append("")

        # 分析趋势
        latest = df.iloc[0]
        oldest = df.iloc[-1]
        rzye_change = (latest.get('rzye', 0) - oldest.get('rzye', 0)) / oldest.get('rzye', 1) * 100 if oldest.get('rzye') else 0

        result.append(f"**融资余额变化**: {rzye_change:+.2f}%")
        if rzye_change > 5:
            result.append("**市场情绪**: 融资余额上升，杠杆资金看多")
        elif rzye_change < -5:
            result.append("**市场情绪**: 融资余额下降，杠杆资金谨慎")
        else:
            result.append("**市场情绪**: 融资余额稳定，市场情绪中性")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取融资融券数据失败: {str(e)}"


def get_pmi() -> str:
    """
    获取PMI采购经理指数

    Returns:
        PMI数据的格式化字符串
    """
    try:
        pro = get_pro_api()

        df = pro.cn_pmi()

        if df.empty:
            return "未获取到PMI数据"

        df = df.head(6)  # 最近6个月

        result = []
        result.append("# 宏观经济指标 - PMI\n")
        result.append("## 采购经理指数（最近6个月）\n")
        result.append("| 月份 | 制造业PMI | 新订单 | 生产 | 从业人员 |")
        result.append("|------|----------|--------|------|---------|")

        for _, row in df.iterrows():
            month = row.get('MONTH', 'N/A')
            pmi = row.get('PMI010000', 0)  # 制造业PMI
            new_order = row.get('PMI010100', 0)  # 新订单
            production = row.get('PMI010200', 0)  # 生产
            employment = row.get('PMI010300', 0)  # 从业人员
            result.append(f"| {month} | {pmi:.1f} | {new_order:.1f} | {production:.1f} | {employment:.1f} |")

        result.append("")

        # 分析
        latest_pmi = df.iloc[0].get('PMI010000', 50)
        if latest_pmi > 50:
            result.append(f"**宏观经济分析**: 制造业PMI为{latest_pmi:.1f}，位于扩张区间，经济景气度向好")
        else:
            result.append(f"**宏观经济分析**: 制造业PMI为{latest_pmi:.1f}，位于收缩区间，经济面临压力")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取PMI数据失败: {str(e)}"


def get_dividend(stock_code: str) -> str:
    """
    获取分红送股历史

    Args:
        stock_code: 股票代码

    Returns:
        分红历史的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        df = pro.dividend(ts_code=ts_code)

        if df.empty:
            return f"未找到股票 {stock_code} 的分红历史"

        df = df.head(10)  # 最近10次

        result = []
        result.append("# 分红送股历史\n")
        result.append("| 分红年度 | 每股分红(元) | 送股(股) | 转增(股) | 除权日 |")
        result.append("|---------|------------|---------|---------|--------|")

        for _, row in df.iterrows():
            end_date = row.get('end_date', 'N/A')
            cash_div = row.get('cash_div', 0) if pd.notna(row.get('cash_div')) else 0
            stk_div = row.get('stk_div', 0) if pd.notna(row.get('stk_div')) else 0
            stk_bo = row.get('stk_bo_rate', 0) if pd.notna(row.get('stk_bo_rate')) else 0
            ex_date = row.get('ex_date', 'N/A')
            result.append(f"| {end_date} | {cash_div:.2f} | {stk_div:.2f} | {stk_bo:.2f} | {ex_date} |")

        result.append("")

        # 计算近3年平均股息率（简化计算）
        recent_cash = df.head(3)['cash_div'].sum()
        result.append(f"**近3年累计分红**: {recent_cash:.2f}元/股")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取分红历史失败: {str(e)}"


def get_top_list(stock_code: str, days: int = 30) -> str:
    """
    获取龙虎榜数据

    Args:
        stock_code: 股票代码
        days: 查询天数，默认30天

    Returns:
        龙虎榜数据的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        # TuShare top_list API要求使用trade_date参数
        # 先获取最近的交易日历，然后逐日查询
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        # 获取交易日历
        cal_df = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open='1')
        if cal_df.empty:
            return f"获取交易日历失败"

        trade_dates = cal_df.sort_values('cal_date', ascending=False)['cal_date'].head(days).tolist()

        all_data = []
        for trade_date in trade_dates[:10]:  # 最多查询最近10个交易日
            try:
                df = pro.top_list(trade_date=trade_date, ts_code=ts_code)
                if not df.empty:
                    all_data.append(df)
            except Exception:
                continue

        if not all_data:
            return f"股票 {stock_code} 近期未上龙虎榜"

        df = pd.concat(all_data, ignore_index=True)
        df = df.sort_values('trade_date', ascending=False)

        result = []
        result.append("# 龙虎榜分析\n")

        for _, row in df.iterrows():
            result.append(f"## {row['trade_date']} 龙虎榜\n")
            result.append(f"- **上榜原因**: {row.get('reason', 'N/A')}")
            result.append(f"- **收盘价**: {row.get('close', 0):.2f}元")
            result.append(f"- **涨跌幅**: {row.get('pct_change', 0):.2f}%")
            result.append(f"- **换手率**: {row.get('turnover_rate', 0):.2f}%")

            l_buy = row.get('l_buy', 0) / 1e8 if pd.notna(row.get('l_buy')) else 0
            l_sell = row.get('l_sell', 0) / 1e8 if pd.notna(row.get('l_sell')) else 0
            net = row.get('net_amount', 0) / 1e8 if pd.notna(row.get('net_amount')) else 0

            result.append(f"- **龙虎榜买入**: {l_buy:.2f}亿元")
            result.append(f"- **龙虎榜卖出**: {l_sell:.2f}亿元")
            result.append(f"- **净买入**: {net:+.2f}亿元")
            result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取龙虎榜数据失败: {str(e)}"


# 综合数据获取函数（供工具调用）

def get_china_stock_comprehensive(stock_code: str, trade_date: Optional[str] = None) -> str:
    """
    获取中国A股综合数据

    Args:
        stock_code: 股票代码
        trade_date: 交易日期

    Returns:
        综合数据的格式化字符串
    """
    result = []

    # 基本信息
    result.append(get_stock_basic_info(stock_code))

    # 估值数据
    result.append(get_daily_basic(stock_code, trade_date))

    # 财务指标
    result.append(get_financial_indicators(stock_code))

    # 业绩预告
    result.append(get_forecast(stock_code))

    return "\n".join(result)


def get_china_stock_fundamentals(stock_code: str) -> str:
    """
    获取基本面综合数据

    Args:
        stock_code: 股票代码

    Returns:
        基本面数据的格式化字符串
    """
    result = []

    # 财务报表
    result.append(get_financial_statements(stock_code))

    # 财务指标
    result.append(get_financial_indicators(stock_code))

    # 业绩预告
    result.append(get_forecast(stock_code))

    # 分红历史
    result.append(get_dividend(stock_code))

    return "\n".join(result)


def get_china_stock_sentiment(stock_code: str) -> str:
    """
    获取市场情绪综合数据

    Args:
        stock_code: 股票代码

    Returns:
        市场情绪数据的格式化字符串
    """
    result = []

    # 资金流向
    result.append(get_moneyflow(stock_code))

    # 北向资金
    result.append(get_hsgt_flow())

    # 融资融券
    result.append(get_margin_data(stock_code))

    # 股东数据
    result.append(get_top10_holders(stock_code))
    result.append(get_holder_number(stock_code))

    return "\n".join(result)


# ============= 新增数据源函数（Phase 1.1 扩展） =============


# ============= 已废弃函数说明 =============
#
# get_hk_hold() 函数已移除
# 废弃原因：港交所自2024年8月20日起停止披露北向资金每日数据
# hk_hold API 目前仅返回季度数据（每年3/6/9/12月），无法用于短期交易分析
#
# 替代方案：
# 1. get_hsgt_top10() - 查看每日北向资金十大成交股
# 2. get_top10_holders() - 通过"香港中央结算"持股比例季度变化判断外资态度
# ============================================


def get_hsgt_top10(trade_date: Optional[str] = None) -> str:
    """
    获取沪深港通十大成交股

    Args:
        trade_date: 交易日期 YYYYMMDD，默认最近交易日

    Returns:
        格式化字符串，包含买入/卖出成交额前10、净买入金额
    """
    try:
        pro = get_pro_api()

        if trade_date is None:
            # 获取最近交易日
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
            # 先获取一条数据确定最新交易日
            df_check = pro.hsgt_top10(start_date=start_date, end_date=end_date)
            if df_check.empty:
                return "未获取到沪深港通十大成交股数据"
            trade_date = df_check['trade_date'].max()

        # 获取沪股通十大 (market_type='1') 和深股通十大 (market_type='3')
        df_sh = pro.hsgt_top10(trade_date=trade_date, market_type='1')
        df_sz = pro.hsgt_top10(trade_date=trade_date, market_type='3')

        result = []
        result.append(f"# 沪深港通十大成交股 ({trade_date})\n")

        if not df_sh.empty:
            result.append("## 沪股通十大成交股\n")
            result.append("| 排名 | 代码 | 名称 | 收盘价 | 涨跌幅(%) | 净买入(万) |")
            result.append("|------|------|------|--------|----------|-----------|")
            for _, row in df_sh.head(10).iterrows():
                rank = row.get('rank', 0)
                ts_code = row.get('ts_code', 'N/A')
                name = row.get('name', 'N/A')[:8]
                close = row.get('close', 0)
                change = row.get('change', 0) if pd.notna(row.get('change')) else 0
                net_amount = row.get('net_amount', 0) / 10000 if pd.notna(row.get('net_amount')) else 0
                result.append(f"| {rank} | {ts_code} | {name} | {close:.2f} | {change:.2f} | {net_amount:+.2f} |")
            result.append("")

        if not df_sz.empty:
            result.append("## 深股通十大成交股\n")
            result.append("| 排名 | 代码 | 名称 | 收盘价 | 涨跌幅(%) | 净买入(万) |")
            result.append("|------|------|------|--------|----------|-----------|")
            for _, row in df_sz.head(10).iterrows():
                rank = row.get('rank', 0)
                ts_code = row.get('ts_code', 'N/A')
                name = row.get('name', 'N/A')[:8]
                close = row.get('close', 0)
                change = row.get('change', 0) if pd.notna(row.get('change')) else 0
                net_amount = row.get('net_amount', 0) / 10000 if pd.notna(row.get('net_amount')) else 0
                result.append(f"| {rank} | {ts_code} | {name} | {close:.2f} | {change:.2f} | {net_amount:+.2f} |")
            result.append("")

        return "\n".join(result) if result else "未获取到沪深港通十大成交股数据"

    except Exception as e:
        return f"获取沪深港通十大成交股数据失败: {str(e)}"


def get_block_trade(stock_code: str, days: int = 30) -> str:
    """
    获取大宗交易数据

    Args:
        stock_code: 股票代码
        days: 获取天数

    Returns:
        格式化字符串，包含交易日期、成交价、折溢价率、买卖营业部
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        df = pro.block_trade(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df.empty:
            return f"股票 {stock_code} 近期无大宗交易记录"

        df = df.head(20)  # 最近20笔

        result = []
        result.append("# 大宗交易分析\n")
        result.append(f"## 近期大宗交易记录（{stock_code}）\n")
        result.append("| 日期 | 成交价 | 成交量(万股) | 成交额(万) | 折溢价(%) | 买方 | 卖方 |")
        result.append("|------|--------|------------|----------|----------|------|------|")

        total_vol = 0
        total_amount = 0
        discount_trades = 0

        for _, row in df.iterrows():
            trade_date = row.get('trade_date', 'N/A')
            price = row.get('price', 0)
            vol = row.get('vol', 0) / 10000 if pd.notna(row.get('vol')) else 0  # 股转万股
            amount = row.get('amount', 0) / 10000 if pd.notna(row.get('amount')) else 0  # 元转万元

            # 计算折溢价率（需要当日收盘价）
            # 简化处理：显示为N/A，或通过其他方式获取
            discount = "N/A"

            buyer = row.get('buyer', 'N/A')[:10] if row.get('buyer') else 'N/A'
            seller = row.get('seller', 'N/A')[:10] if row.get('seller') else 'N/A'

            result.append(f"| {trade_date} | {price:.2f} | {vol:.2f} | {amount:.2f} | {discount} | {buyer} | {seller} |")

            total_vol += vol
            total_amount += amount

        result.append("")
        result.append(f"**统计汇总**: 共{len(df)}笔大宗交易")
        result.append(f"**累计成交**: {total_vol:.2f}万股，{total_amount:.2f}万元")

        # 分析
        if len(df) >= 5:
            result.append("")
            result.append("**风险提示**: 近期大宗交易频繁，需关注是否存在减持压力")

        result.append("")
        return "\n".join(result)

    except Exception as e:
        return f"获取大宗交易数据失败: {str(e)}"


def get_pledge_stat(stock_code: str) -> str:
    """
    获取股权质押统计

    Args:
        stock_code: 股票代码

    Returns:
        格式化字符串，包含质押总股数、质押比例、风险提示
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        df = pro.pledge_stat(ts_code=ts_code)

        if df.empty:
            return f"未找到股票 {stock_code} 的股权质押数据"

        df = df.head(8)  # 最近8期

        result = []
        result.append("# 股权质押分析\n")
        result.append("## 股权质押统计\n")
        result.append("| 截止日期 | 质押次数 | 无限售质押(万股) | 限售质押(万股) | 总股本(万股) | 质押比例(%) |")
        result.append("|---------|---------|----------------|--------------|------------|------------|")

        latest_ratio = 0
        for _, row in df.iterrows():
            end_date = row.get('end_date', 'N/A')
            pledge_count = row.get('pledge_count', 0)
            unrest_pledge = row.get('unrest_pledge', 0) / 10000 if pd.notna(row.get('unrest_pledge')) else 0
            rest_pledge = row.get('rest_pledge', 0) / 10000 if pd.notna(row.get('rest_pledge')) else 0
            total_share = row.get('total_share', 0) / 10000 if pd.notna(row.get('total_share')) else 0
            pledge_ratio = row.get('pledge_ratio', 0) if pd.notna(row.get('pledge_ratio')) else 0

            if latest_ratio == 0:
                latest_ratio = pledge_ratio

            result.append(f"| {end_date} | {pledge_count} | {unrest_pledge:.2f} | {rest_pledge:.2f} | {total_share:.2f} | {pledge_ratio:.2f} |")

        result.append("")

        # 风险评估
        if latest_ratio > 50:
            risk_level = "【高风险】质押比例超过50%，存在重大平仓风险"
        elif latest_ratio > 30:
            risk_level = "【中风险】质押比例较高，需密切关注股价波动"
        elif latest_ratio > 10:
            risk_level = "【低风险】质押比例适中，风险可控"
        else:
            risk_level = "【安全】质押比例较低，无明显风险"

        result.append(f"**当前质押比例**: {latest_ratio:.2f}%")
        result.append(f"**风险评估**: {risk_level}")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取股权质押数据失败: {str(e)}"


def get_share_float(stock_code: str) -> str:
    """
    获取限售解禁日历

    Args:
        stock_code: 股票代码

    Returns:
        格式化字符串，包含未来解禁日期、解禁数量及占比
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        df = pro.share_float(ts_code=ts_code)

        if df.empty:
            return f"未找到股票 {stock_code} 的解禁数据"

        # 筛选未来6个月的解禁
        today = datetime.now().strftime('%Y%m%d')
        future_date = (datetime.now() + timedelta(days=180)).strftime('%Y%m%d')

        # 过滤未来解禁
        df_future = df[(df['float_date'] >= today) & (df['float_date'] <= future_date)]

        result = []
        result.append("# 限售解禁日历\n")

        if df_future.empty:
            result.append("## 未来6个月无重大解禁\n")
            result.append("该股票未来6个月内暂无限售股解禁安排。\n")
        else:
            result.append("## 未来6个月解禁计划\n")
            result.append("| 解禁日期 | 解禁数量(万股) | 占总股本(%) | 股东名称 | 解禁类型 |")
            result.append("|---------|--------------|------------|---------|---------|")

            total_float = 0
            for _, row in df_future.iterrows():
                float_date = row.get('float_date', 'N/A')
                float_share = row.get('float_share', 0) / 10000 if pd.notna(row.get('float_share')) else 0
                float_ratio = row.get('float_ratio', 0) if pd.notna(row.get('float_ratio')) else 0
                holder_name = row.get('holder_name', 'N/A')[:15] if row.get('holder_name') else 'N/A'
                share_type = row.get('share_type', 'N/A')

                result.append(f"| {float_date} | {float_share:.2f} | {float_ratio:.2f} | {holder_name} | {share_type} |")
                total_float += float_share

            result.append("")
            result.append(f"**未来6个月累计解禁**: {total_float:.2f}万股")

            # 风险提示
            if total_float > 10000:  # 超过1亿股
                result.append("**风险提示**: 解禁规模较大，可能对股价形成压力")

        result.append("")

        # 显示历史解禁情况
        df_past = df[df['float_date'] < today].head(5)
        if not df_past.empty:
            result.append("## 近期已解禁记录\n")
            result.append("| 解禁日期 | 解禁数量(万股) | 占总股本(%) |")
            result.append("|---------|--------------|------------|")
            for _, row in df_past.iterrows():
                float_date = row.get('float_date', 'N/A')
                float_share = row.get('float_share', 0) / 10000 if pd.notna(row.get('float_share')) else 0
                float_ratio = row.get('float_ratio', 0) if pd.notna(row.get('float_ratio')) else 0
                result.append(f"| {float_date} | {float_share:.2f} | {float_ratio:.2f} |")
            result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取解禁数据失败: {str(e)}"


def get_index_daily(index_code: str, days: int = 60) -> str:
    """
    获取指数日线行情

    Args:
        index_code: 指数代码（如 000300.SH 沪深300, 399006.SZ 创业板指, 399318.SZ 有色金属）
        days: 获取天数

    Returns:
        格式化字符串，包含指数收盘价、涨跌幅、成交额
    """
    try:
        pro = get_pro_api()

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        df = pro.index_daily(ts_code=index_code, start_date=start_date, end_date=end_date)

        if df.empty:
            return f"未找到指数 {index_code} 的行情数据"

        df = df.head(days)

        # 获取指数名称
        index_name_map = {
            '000300.SH': '沪深300',
            '399006.SZ': '创业板指',
            '399318.SZ': '国证有色',
            '000016.SH': '上证50',
            '399001.SZ': '深证成指',
            '000001.SH': '上证指数',
        }
        index_name = index_name_map.get(index_code, index_code)

        result = []
        result.append(f"# {index_name}({index_code}) 行情分析\n")
        result.append(f"## 近期走势（最近{min(len(df), 20)}个交易日）\n")
        result.append("| 日期 | 收盘 | 涨跌幅(%) | 成交额(亿) | 振幅(%) |")
        result.append("|------|------|----------|----------|--------|")

        for _, row in df.head(20).iterrows():
            trade_date = row.get('trade_date', 'N/A')
            close = row.get('close', 0)
            pct_chg = row.get('pct_chg', 0) if pd.notna(row.get('pct_chg')) else 0
            amount = row.get('amount', 0) / 100000 if pd.notna(row.get('amount')) else 0  # 千元转亿元

            # 计算振幅
            high = row.get('high', 0)
            low = row.get('low', 0)
            pre_close = row.get('pre_close', close)
            amplitude = (high - low) / pre_close * 100 if pre_close > 0 else 0

            result.append(f"| {trade_date} | {close:.2f} | {pct_chg:+.2f} | {amount:.2f} | {amplitude:.2f} |")

        result.append("")

        # 计算统计指标
        latest_close = df.iloc[0]['close']
        oldest_close = df.iloc[-1]['close']
        period_return = (latest_close - oldest_close) / oldest_close * 100

        result.append(f"**区间涨跌幅**: {period_return:+.2f}%（近{len(df)}个交易日）")
        result.append(f"**最新收盘**: {latest_close:.2f}")

        # 均值分析
        avg_amount = df['amount'].mean() / 100000
        result.append(f"**日均成交额**: {avg_amount:.2f}亿元")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取指数行情数据失败: {str(e)}"


def get_index_member(index_code: str = "399318.SZ") -> str:
    """
    获取指数成分股

    Args:
        index_code: 指数代码，默认为有色金属指数 399318.SZ

    Returns:
        格式化字符串，包含成分股列表
    """
    try:
        pro = get_pro_api()

        index_name_map = {
            '399318.SZ': '国证有色',
            '000300.SH': '沪深300',
            '399006.SZ': '创业板指',
            '000016.SH': '上证50',
            '000905.SH': '中证500',
            '399001.SZ': '深证成指',
            '000001.SH': '上证指数',
            '399673.SZ': '创业板50',
            '000688.SH': '科创50',
        }
        index_name = index_name_map.get(index_code, index_code)

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

        df = pd.DataFrame()

        # 方法1: 使用 index_member API（主流指数）
        try:
            df = pro.index_member(index_code=index_code)
        except:
            pass

        # 方法2: 如果为空，尝试使用 index_weight API（获取权重数据）
        if df.empty:
            try:
                df_weight = pro.index_weight(index_code=index_code, start_date=start_date, end_date=end_date)
                if not df_weight.empty:
                    # 获取最新日期的权重数据
                    latest_date = df_weight['trade_date'].max()
                    df_latest = df_weight[df_weight['trade_date'] == latest_date].copy()

                    result = []
                    result.append(f"# {index_name}({index_code}) 成分股权重\n")
                    result.append(f"## 最新成分股列表（{latest_date}，共{len(df_latest)}只）\n")
                    result.append("| 代码 | 权重(%) |")
                    result.append("|------|--------|")

                    df_latest = df_latest.sort_values('weight', ascending=False)
                    for _, row in df_latest.head(30).iterrows():
                        con_code = row.get('con_code', 'N/A')
                        weight = row.get('weight', 0)
                        result.append(f"| {con_code} | {weight:.2f} |")

                    if len(df_latest) > 30:
                        result.append(f"\n*注：仅显示权重前30只成分股，共{len(df_latest)}只*")

                    result.append("")
                    return "\n".join(result)
            except:
                pass

        # 方法3: 对于国证系列指数，尝试使用 ths_member（同花顺概念板块）
        if df.empty and index_code.startswith('399'):
            try:
                # 尝试获取同花顺行业成分
                df_ths = pro.ths_member(ts_code=index_code)
                if not df_ths.empty:
                    result = []
                    result.append(f"# {index_name}({index_code}) 成分股\n")
                    result.append(f"## 同花顺板块成分（共{len(df_ths)}只）\n")
                    result.append("| 代码 | 名称 |")
                    result.append("|------|------|")

                    for _, row in df_ths.head(30).iterrows():
                        code = row.get('code', 'N/A')
                        name = row.get('name', 'N/A')
                        result.append(f"| {code} | {name} |")

                    if len(df_ths) > 30:
                        result.append(f"\n*注：仅显示前30只成分股，共{len(df_ths)}只*")
                    result.append("")
                    return "\n".join(result)
            except:
                pass

        # 方法4: 对于特定行业指数，返回行业说明
        if df.empty:
            # 国证系列行业指数可能没有成分股API，返回说明信息
            industry_indices = {
                '399318.SZ': '有色金属',
                '399395.SZ': '国证银行',
                '399396.SZ': '国证食品',
                '399441.SZ': '国证生科',
            }
            if index_code in industry_indices:
                industry = industry_indices[index_code]
                return (f"# {index_name}({index_code})\n\n"
                        f"该指数为国证系列{industry}行业指数，TuShare暂未提供成分股明细数据。\n\n"
                        f"**建议**: 使用 get_index_daily API 获取指数行情走势，与个股进行联动分析。\n\n"
                        f"*提示: 可通过国证指数官网查询完整成分股列表*")

            return f"未找到指数 {index_code} 的成分股数据（该指数可能不在TuShare数据覆盖范围内，建议使用沪深300/上证50等主流指数）"

        # 过滤当前有效的成分股（out_date为空或大于今天）
        today = datetime.now().strftime('%Y%m%d')
        df_valid = df[(df['out_date'].isna()) | (df['out_date'] > today)]

        result = []
        result.append(f"# {index_name}({index_code}) 成分股\n")
        result.append(f"## 当前成分股列表（共{len(df_valid)}只）\n")
        result.append("| 代码 | 名称 | 纳入日期 |")
        result.append("|------|------|---------|")

        for _, row in df_valid.head(30).iterrows():  # 最多显示30只
            con_code = row.get('con_code', 'N/A')
            con_name = row.get('con_name', 'N/A')
            in_date = row.get('in_date', 'N/A')
            result.append(f"| {con_code} | {con_name} | {in_date} |")

        if len(df_valid) > 30:
            result.append(f"\n*注：仅显示前30只成分股，共{len(df_valid)}只*")

        result.append("")
        return "\n".join(result)

    except Exception as e:
        return f"获取指数成分股数据失败: {str(e)}"


def get_stk_surv(stock_code: str) -> str:
    """
    获取机构调研数据

    Args:
        stock_code: 股票代码

    Returns:
        格式化字符串，包含近期调研记录
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        # 获取最近6个月的调研数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')

        df = pro.stk_surv(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df.empty:
            return f"股票 {stock_code} 近6个月无机构调研记录"

        # 注意：stk_surv API 每行返回一家机构的调研记录
        # 字段：surv_date(调研日期), rece_org(接待机构), org_type(机构类型), rece_mode(接待方式)
        # 需要按日期分组统计

        result = []
        result.append("# 机构调研分析\n")
        result.append(f"## 近期机构调研记录（{stock_code}）\n")

        # 按日期分组统计
        date_stats = {}
        org_type_stats = {}

        for _, row in df.iterrows():
            surv_date = row.get('surv_date', 'N/A')
            org_type = row.get('org_type', '其他')
            rece_mode = row.get('rece_mode', 'N/A')
            rece_org = row.get('rece_org', 'N/A')

            # 按日期统计
            if surv_date not in date_stats:
                date_stats[surv_date] = {'count': 0, 'modes': set(), 'orgs': []}
            date_stats[surv_date]['count'] += 1
            if rece_mode and rece_mode != 'N/A':
                date_stats[surv_date]['modes'].add(rece_mode.split(',')[0])  # 取第一个模式
            date_stats[surv_date]['orgs'].append(rece_org)

            # 按机构类型统计
            if org_type:
                org_type_stats[org_type] = org_type_stats.get(org_type, 0) + 1

        # 输出按日期的调研汇总（最近10个日期）
        result.append("| 调研日期 | 机构数量 | 调研形式 | 参与机构（部分） |")
        result.append("|---------|---------|---------|----------------|")

        sorted_dates = sorted(date_stats.keys(), reverse=True)[:10]
        for date in sorted_dates:
            stats = date_stats[date]
            modes = '/'.join(list(stats['modes'])[:2]) if stats['modes'] else 'N/A'
            orgs_preview = ', '.join(stats['orgs'][:3])
            if len(stats['orgs']) > 3:
                orgs_preview += f" 等{len(stats['orgs'])}家"
            result.append(f"| {date} | {stats['count']} | {modes} | {orgs_preview} |")

        result.append("")

        # 机构类型分布
        result.append("### 机构类型分布")
        result.append("| 机构类型 | 参与次数 |")
        result.append("|---------|---------|")
        for org_type, count in sorted(org_type_stats.items(), key=lambda x: x[1], reverse=True):
            result.append(f"| {org_type} | {count} |")

        result.append("")
        total_records = len(df)
        unique_dates = len(date_stats)
        result.append(f"**调研统计**: 近6个月共{unique_dates}次调研活动，累计{total_records}家机构参与")

        # 分析
        if unique_dates >= 5:
            result.append("")
            result.append("**调研密度分析**: 调研频繁，机构关注度较高")
        elif unique_dates >= 2:
            result.append("")
            result.append("**调研密度分析**: 调研活动正常，机构保持关注")

        result.append("")
        return "\n".join(result)

    except Exception as e:
        return f"获取机构调研数据失败: {str(e)}"


def get_report_rc(stock_code: str, days: int = 30) -> str:
    """
    获取券商研报数据

    Args:
        stock_code: 股票代码
        days: 获取天数

    Returns:
        格式化字符串，包含近期研报标题、评级、目标价
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        df = pro.report_rc(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df.empty:
            return f"股票 {stock_code} 近期无券商研报"

        df = df.head(15)  # 最近15篇

        result = []
        result.append("# 券商研报分析\n")
        result.append(f"## 近期券商研报（{stock_code}）\n")
        result.append("| 日期 | 机构 | 评级 | 目标价 | 研报标题 |")
        result.append("|------|------|------|--------|---------|")

        rating_count = {'买入': 0, '增持': 0, '持有': 0, '减持': 0, '卖出': 0, '其他': 0}
        target_prices = []

        for _, row in df.iterrows():
            report_date = row.get('report_date', 'N/A')
            organ_name = row.get('organ_name', 'N/A')[:8] if row.get('organ_name') else 'N/A'
            rating = row.get('rating', 'N/A')
            target_price = row.get('target_price', None)
            title = row.get('report_title', 'N/A')[:25] if row.get('report_title') else 'N/A'

            # 统计评级
            if rating in rating_count:
                rating_count[rating] += 1
            else:
                rating_count['其他'] += 1

            # 收集目标价
            if target_price and pd.notna(target_price) and target_price > 0:
                target_prices.append(target_price)

            tp_str = f"{target_price:.2f}" if target_price and pd.notna(target_price) and target_price > 0 else "-"
            result.append(f"| {report_date} | {organ_name} | {rating} | {tp_str} | {title} |")

        result.append("")

        # 评级统计
        result.append("## 评级统计\n")
        result.append(f"- **买入/增持**: {rating_count['买入'] + rating_count['增持']}家")
        result.append(f"- **持有**: {rating_count['持有']}家")
        result.append(f"- **减持/卖出**: {rating_count['减持'] + rating_count['卖出']}家")

        # 目标价统计
        if target_prices:
            avg_target = sum(target_prices) / len(target_prices)
            max_target = max(target_prices)
            min_target = min(target_prices)
            result.append("")
            result.append("## 目标价统计\n")
            result.append(f"- **平均目标价**: {avg_target:.2f}元")
            result.append(f"- **最高目标价**: {max_target:.2f}元")
            result.append(f"- **最低目标价**: {min_target:.2f}元")

        result.append("")
        return "\n".join(result)

    except Exception as e:
        return f"获取券商研报数据失败: {str(e)}"


def get_fut_daily(fut_code: str, days: int = 60) -> str:
    """
    获取期货日线数据（铜/金主力合约）

    Args:
        fut_code: 期货代码（如 CU.SHF 沪铜, AU.SHF 沪金）
                  常用代码: CU=铜, AU=黄金, AG=白银, AL=铝
        days: 获取天数

    Returns:
        格式化字符串，包含期货价格走势
    """
    try:
        pro = get_pro_api()

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        # 获取主力合约映射
        # 首先尝试获取主力合约代码
        df_mapping = pro.fut_mapping(ts_code=fut_code)
        if not df_mapping.empty:
            # 使用主力合约
            main_contract = df_mapping.iloc[0]['mapping_ts_code']
        else:
            main_contract = fut_code

        df = pro.fut_daily(ts_code=main_contract, start_date=start_date, end_date=end_date)

        if df.empty:
            return f"未找到期货 {fut_code} 的行情数据"

        df = df.head(days)

        # 期货名称映射
        fut_name_map = {
            'CU': '沪铜',
            'AU': '沪金',
            'AG': '沪银',
            'AL': '沪铝',
            'ZN': '沪锌',
            'PB': '沪铅',
            'NI': '沪镍',
            'SN': '沪锡',
        }
        fut_prefix = fut_code.split('.')[0][:2] if '.' in fut_code else fut_code[:2]
        fut_name = fut_name_map.get(fut_prefix, fut_code)

        result = []
        result.append(f"# {fut_name} 期货行情分析\n")
        result.append(f"## 主力合约走势（{main_contract}）\n")
        result.append("| 日期 | 收盘价 | 结算价 | 涨跌幅(%) | 成交量(手) | 持仓量(手) |")
        result.append("|------|--------|--------|----------|-----------|-----------|")

        for _, row in df.head(20).iterrows():
            trade_date = row.get('trade_date', 'N/A')
            close = row.get('close', 0)
            settle = row.get('settle', 0)
            # 计算涨跌幅
            pre_settle = row.get('pre_settle', settle)
            pct_chg = (close - pre_settle) / pre_settle * 100 if pre_settle > 0 else 0
            vol = row.get('vol', 0)
            oi = row.get('oi', 0)

            result.append(f"| {trade_date} | {close:.0f} | {settle:.0f} | {pct_chg:+.2f} | {vol:.0f} | {oi:.0f} |")

        result.append("")

        # 统计分析
        latest_close = df.iloc[0]['close']
        oldest_close = df.iloc[-1]['close']
        period_return = (latest_close - oldest_close) / oldest_close * 100

        result.append(f"**区间涨跌幅**: {period_return:+.2f}%（近{len(df)}个交易日）")
        result.append(f"**最新收盘价**: {latest_close:.0f}")

        # 趋势判断
        if period_return > 5:
            trend = "期货价格上涨趋势明显，对相关股票形成利好"
        elif period_return < -5:
            trend = "期货价格下跌趋势，可能影响相关股票盈利预期"
        else:
            trend = "期货价格震荡，短期影响有限"

        result.append(f"**趋势判断**: {trend}")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取期货行情数据失败: {str(e)}"


# ============= 扩展综合数据获取函数 =============


def get_china_stock_capital_deep(stock_code: str) -> str:
    """
    获取深度资金分析数据（整合大宗交易、股权质押、解禁日历等）

    注：北向资金持股明细(hk_hold)已移除，港交所自2024年8月20日起仅提供季度数据。
    外资态度可通过前十大股东中"香港中央结算"持股比例变化来判断。

    Args:
        stock_code: 股票代码

    Returns:
        深度资金分析数据的格式化字符串
    """
    result = []

    # 大宗交易
    result.append(get_block_trade(stock_code))

    # 股权质押
    result.append(get_pledge_stat(stock_code))

    # 解禁日历
    result.append(get_share_float(stock_code))

    return "\n".join(result)


def get_china_stock_institution(stock_code: str) -> str:
    """
    获取机构观点数据（整合调研、研报）

    Args:
        stock_code: 股票代码

    Returns:
        机构观点数据的格式化字符串
    """
    result = []

    # 机构调研
    result.append(get_stk_surv(stock_code))

    # 券商研报
    result.append(get_report_rc(stock_code))

    return "\n".join(result)


# ==================== 新闻数据接口 ====================

def get_cctv_news(date: str = None) -> str:
    """
    获取新闻联播文字稿

    Args:
        date: 日期，格式 YYYYMMDD，默认今天

    Returns:
        新闻联播内容的格式化字符串
    """
    try:
        pro = get_pro_api()
    except ValueError as e:
        return f"[数据获取失败] {str(e)}"

    try:
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        df = pro.cctv_news(date=date)

        if df is None or df.empty:
            return f"[无数据] {date} 无新闻联播数据"

        result = [f"# 新闻联播 ({date})\n"]

        # 筛选经济相关新闻
        economic_keywords = ['经济', '金融', '股市', '投资', '贸易', '产业', '制造', '科技', '改革', '发展', '企业']

        for idx, row in df.iterrows():
            title = row.get('title', '')
            content = row.get('content', '')

            # 检查是否与经济相关
            is_economic = any(kw in title or kw in str(content)[:200] for kw in economic_keywords)

            if is_economic:
                result.append(f"## {title}\n")
                if content:
                    # 截断过长内容
                    content_preview = content[:500] + '...' if len(str(content)) > 500 else content
                    result.append(f"{content_preview}\n")

        if len(result) == 1:
            result.append("今日无经济相关重点新闻")

        return "\n".join(result)

    except Exception as e:
        return f"[数据获取失败] 获取新闻联播数据失败: {str(e)}"


def get_major_news(start_date: str = None, end_date: str = None, src: str = None) -> str:
    """
    获取重大新闻（需要单独开通权限）

    Args:
        start_date: 开始日期时间，格式 'YYYY-MM-DD HH:MM:SS'
        end_date: 结束日期时间，格式 'YYYY-MM-DD HH:MM:SS'
        src: 新闻来源，如 '新浪财经', '同花顺'

    Returns:
        重大新闻的格式化字符串
    """
    try:
        pro = get_pro_api()
    except ValueError as e:
        return f"[数据获取失败] {str(e)}"

    try:
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if start_date is None:
            # 默认获取最近24小时的新闻
            start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

        params = {
            'start_date': start_date,
            'end_date': end_date,
        }
        if src:
            params['src'] = src

        df = pro.major_news(**params)

        if df is None or df.empty:
            return "[无数据] 无重大新闻数据（可能需要开通权限）"

        result = ["# 重大财经新闻\n"]

        for idx, row in df.head(20).iterrows():
            title = row.get('title', '')
            pub_time = row.get('pub_time', '')
            source = row.get('src', '')
            content = row.get('content', '')

            result.append(f"**[{pub_time}] [{source}]** {title}")
            if content:
                content_preview = content[:300] + '...' if len(str(content)) > 300 else content
                result.append(f"  {content_preview}")
            result.append("")

        return "\n".join(result)

    except Exception as e:
        error_msg = str(e)
        if '权限' in error_msg or 'permission' in error_msg.lower():
            return "[权限不足] 重大新闻接口需要单独开通权限，请联系 Tushare"
        return f"[数据获取失败] 获取重大新闻失败: {error_msg}"


def get_china_market_news_tushare(date: str = None) -> str:
    """
    获取中国财经市场新闻（Tushare 版本）

    整合新闻联播和重大新闻数据

    Args:
        date: 日期，格式 YYYY-MM-DD 或 YYYYMMDD

    Returns:
        格式化的市场新闻字符串
    """
    result_parts = ["# 中国财经市场新闻 (Tushare)\n"]

    # 格式化日期
    if date:
        date_clean = date.replace("-", "")
    else:
        date_clean = datetime.now().strftime("%Y%m%d")

    # 1. 获取新闻联播
    cctv_result = get_cctv_news(date_clean)
    if "[数据获取失败]" not in cctv_result and "[无数据]" not in cctv_result:
        result_parts.append(cctv_result)
        result_parts.append("\n---\n")

    # 2. 尝试获取重大新闻（可能没有权限）
    major_result = get_major_news()
    if "[权限不足]" not in major_result and "[数据获取失败]" not in major_result:
        result_parts.append(major_result)
    else:
        result_parts.append("## 财经快讯\n")
        result_parts.append("重大新闻接口暂不可用，请参考新闻联播内容或使用其他新闻源。\n")

    return "\n".join(result_parts)
