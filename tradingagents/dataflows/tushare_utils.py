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
from typing import Optional
from datetime import datetime, timedelta

import tushare as ts
import pandas as pd


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


def get_stock_basic_info(stock_code: str) -> str:
    """
    获取股票基本信息

    Args:
        stock_code: 股票代码

    Returns:
        股票基本信息的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        df = pro.stock_basic(ts_code=ts_code,
                            fields='ts_code,symbol,name,area,industry,fullname,list_date,market')

        if df.empty:
            return f"未找到股票 {stock_code} 的基本信息"

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
        return f"获取股票基本信息失败: {str(e)}"


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

        df = pro.fina_indicator(ts_code=ts_code,
                               fields='ts_code,end_date,eps,bps,roe,roa,gross_margin,netprofit_margin,debt_to_assets,current_ratio,quick_ratio,netprofit_yoy,tr_yoy')

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
            gm = row['gross_margin'] if pd.notna(row['gross_margin']) else 0
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

        # 计算平均值
        result.append("")
        avg_pe = df['pe'].mean()
        avg_pb = df['pb'].mean()
        latest = df.iloc[0]
        result.append(f"**最新估值**: PE={latest['pe']:.2f}, PB={latest['pb']:.2f}")
        result.append(f"**近期平均**: PE={avg_pe:.2f}, PB={avg_pb:.2f}")
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
    获取沪深港通资金流向（北向资金）

    Returns:
        北向资金流向的格式化字符串
    """
    try:
        pro = get_pro_api()

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

        df = pro.moneyflow_hsgt(start_date=start_date, end_date=end_date)

        if df.empty:
            return "未获取到北向资金数据"

        df = df.head(10)  # 最近10天

        result = []
        result.append("# 北向资金流向\n")
        result.append("## 沪深港通资金流向（最近10个交易日）\n")
        result.append("| 日期 | 沪股通(亿) | 深股通(亿) | 北向合计(亿) |")
        result.append("|------|-----------|-----------|-------------|")

        for _, row in df.iterrows():
            hgt = row.get('hgt', 0) / 10000 if pd.notna(row.get('hgt')) else 0  # 万元转亿元
            sgt = row.get('sgt', 0) / 10000 if pd.notna(row.get('sgt')) else 0
            north = row.get('north_money', 0) / 10000 if pd.notna(row.get('north_money')) else 0
            result.append(f"| {row['trade_date']} | {hgt:+.2f} | {sgt:+.2f} | {north:+.2f} |")

        result.append("")

        # 计算累计
        total_north = df['north_money'].sum() / 10000
        result.append(f"**近10日北向资金累计流入**: {total_north:+.2f}亿元")

        if total_north > 50:
            result.append("**北向资金态度**: 持续大幅流入，外资看好A股")
        elif total_north > 0:
            result.append("**北向资金态度**: 小幅净流入，外资态度偏积极")
        elif total_north > -50:
            result.append("**北向资金态度**: 小幅净流出，外资态度谨慎")
        else:
            result.append("**北向资金态度**: 持续流出，外资态度偏悲观")
        result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"获取北向资金数据失败: {str(e)}"


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


def get_top_list(stock_code: str) -> str:
    """
    获取龙虎榜数据

    Args:
        stock_code: 股票代码

    Returns:
        龙虎榜数据的格式化字符串
    """
    try:
        pro = get_pro_api()
        ts_code = convert_stock_code(stock_code)

        # 获取最近30天的龙虎榜数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

        df = pro.top_list(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df.empty:
            return f"股票 {stock_code} 近期未上龙虎榜"

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
