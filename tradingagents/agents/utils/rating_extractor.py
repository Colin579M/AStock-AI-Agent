"""
评级提取模块

从各分析师报告中提取评级、核心发现等关键信息，
供研究主管进行一致性检查和综合决策。
"""

import re
from typing import Dict, Any, Optional


def extract_rating_from_fundamentals_report(report: str) -> Dict[str, Any]:
    """
    从基本面报告中提取评级和核心发现

    Args:
        report: 基本面分析报告文本

    Returns:
        包含评级和核心发现的字典
    """
    if not report:
        return {"rating": "未明确", "summary": "无基本面报告"}

    result = {
        "rating": "未明确",
        "target_price": None,
        "risk_reward_ratio": None,
        "safety_margin": None,
        "core_finding": ""
    }

    # 提取盈亏比
    ratio_patterns = [
        r'盈亏比[：:\s]*([\d.]+)',
        r'盈亏比[：:\s]*约?([\d.]+)',
        r'风险收益比[：:\s]*([\d.]+)',
    ]
    for pattern in ratio_patterns:
        ratio_match = re.search(pattern, report)
        if ratio_match:
            try:
                result["risk_reward_ratio"] = float(ratio_match.group(1))
            except ValueError:
                pass
            break

    # 提取目标价
    target_patterns = [
        r'目标价[：:\s]*([\d.]+)元',
        r'加权目标价[：:\s]*([\d.]+)',
        r'中性目标价[：:\s]*([\d.]+)',
    ]
    for pattern in target_patterns:
        target_match = re.search(pattern, report)
        if target_match:
            try:
                result["target_price"] = float(target_match.group(1))
            except ValueError:
                pass
            break

    # 提取安全边际
    margin_match = re.search(r'安全边际[：:\s]*([\d.]+)%?', report)
    if margin_match:
        try:
            result["safety_margin"] = float(margin_match.group(1))
        except ValueError:
            pass

    # 推断评级
    if "极佳" in report:
        result["rating"] = "强烈买入"
        result["core_finding"] = "盈亏比极佳，悲观情景仍有上涨空间"
    elif result["risk_reward_ratio"]:
        if result["risk_reward_ratio"] > 3:
            result["rating"] = "强烈买入"
            result["core_finding"] = f"盈亏比{result['risk_reward_ratio']:.1f}，风险收益优异"
        elif result["risk_reward_ratio"] > 2:
            result["rating"] = "买入"
            result["core_finding"] = f"盈亏比{result['risk_reward_ratio']:.1f}，具有投资价值"
        elif result["risk_reward_ratio"] > 1:
            result["rating"] = "观望"
            result["core_finding"] = f"盈亏比{result['risk_reward_ratio']:.1f}，风险收益一般"
        else:
            result["rating"] = "卖出"
            result["core_finding"] = f"盈亏比{result['risk_reward_ratio']:.1f}，风险大于收益"

    # 如果有目标价但未推断出评级，检查涨幅空间
    if result["rating"] == "未明确" and result["target_price"]:
        # 尝试提取当前价
        price_match = re.search(r'当前[股]?价[：:\s]*([\d.]+)', report)
        if price_match:
            try:
                current_price = float(price_match.group(1))
                upside = (result["target_price"] - current_price) / current_price * 100
                if upside > 30:
                    result["rating"] = "买入"
                    result["core_finding"] = f"目标价{result['target_price']}元，上涨空间{upside:.0f}%"
                elif upside > 10:
                    result["rating"] = "观望"
                    result["core_finding"] = f"目标价{result['target_price']}元，上涨空间{upside:.0f}%"
                else:
                    result["rating"] = "卖出"
                    result["core_finding"] = f"目标价{result['target_price']}元，空间有限"
            except ValueError:
                pass

    return result


def extract_rating_from_market_report(report: str) -> Dict[str, Any]:
    """
    从技术面/市场报告中提取评级

    Args:
        report: 技术面分析报告文本

    Returns:
        包含评级和技术信号的字典
    """
    if not report:
        return {"rating": "未明确", "summary": "无技术面报告"}

    result = {
        "rating": "未明确",
        "trend": "未知",
        "signal": "",
        "core_finding": ""
    }

    # 检测趋势
    if any(kw in report for kw in ["上升趋势", "多头排列", "突破", "站上"]):
        result["trend"] = "看多"
    elif any(kw in report for kw in ["下降趋势", "空头排列", "破位", "跌破"]):
        result["trend"] = "看空"
    else:
        result["trend"] = "震荡"

    # 检测买入信号
    buy_signals = []
    if "金叉" in report:
        buy_signals.append("金叉")
    if "放量上涨" in report or "量价齐升" in report:
        buy_signals.append("放量上涨")
    if "突破" in report and ("阻力" in report or "压力" in report):
        buy_signals.append("突破阻力")
    if "超卖" in report:
        buy_signals.append("超卖反弹")

    # 检测卖出信号
    sell_signals = []
    if "死叉" in report:
        sell_signals.append("死叉")
    if "放量下跌" in report or "量价齐跌" in report:
        sell_signals.append("放量下跌")
    if "跌破" in report and ("支撑" in report or "均线" in report):
        sell_signals.append("跌破支撑")
    if "超买" in report:
        sell_signals.append("超买回调")

    # 综合判断
    if len(buy_signals) > len(sell_signals) and buy_signals:
        result["rating"] = "买入"
        result["signal"] = "、".join(buy_signals)
        result["core_finding"] = f"技术信号：{result['signal']}"
    elif len(sell_signals) > len(buy_signals) and sell_signals:
        result["rating"] = "卖出"
        result["signal"] = "、".join(sell_signals)
        result["core_finding"] = f"技术信号：{result['signal']}"
    else:
        result["rating"] = "观望"
        if buy_signals or sell_signals:
            result["signal"] = f"多空信号并存"
            result["core_finding"] = f"多空信号并存，暂时观望"
        else:
            result["signal"] = "无明显信号"
            result["core_finding"] = "技术面无明显方向"

    return result


def extract_sentiment_from_news_report(report: str) -> Dict[str, Any]:
    """
    从消息面报告中提取情绪倾向

    Args:
        report: 消息面分析报告文本

    Returns:
        包含情绪评级的字典
    """
    if not report:
        return {"rating": "中性", "summary": "无消息面报告"}

    result = {
        "rating": "中性",
        "positive_count": 0,
        "negative_count": 0,
        "core_finding": ""
    }

    # 统计正面消息
    positive_keywords = ["利好", "增长", "超预期", "新高", "上调", "突破", "看好", "机会"]
    negative_keywords = ["利空", "下滑", "不及预期", "新低", "下调", "暴跌", "风险", "担忧"]

    for kw in positive_keywords:
        result["positive_count"] += report.count(kw)

    for kw in negative_keywords:
        result["negative_count"] += report.count(kw)

    # 综合判断
    net_sentiment = result["positive_count"] - result["negative_count"]
    if net_sentiment > 3:
        result["rating"] = "看多"
        result["core_finding"] = f"正面消息{result['positive_count']}条，消息面偏多"
    elif net_sentiment < -3:
        result["rating"] = "看空"
        result["core_finding"] = f"负面消息{result['negative_count']}条，消息面偏空"
    else:
        result["rating"] = "中性"
        result["core_finding"] = "消息面无明显偏向"

    return result


def extract_sentiment_from_sentiment_report(report: str) -> Dict[str, Any]:
    """
    从情绪面报告中提取市场情绪

    Args:
        report: 情绪面分析报告文本

    Returns:
        包含情绪评级的字典
    """
    if not report:
        return {"rating": "中性", "summary": "无情绪面报告"}

    result = {
        "rating": "中性",
        "sentiment_score": None,
        "core_finding": ""
    }

    # 提取情绪分数
    score_match = re.search(r'情绪[指数分]?[：:\s]*([\d.]+)', report)
    if score_match:
        try:
            result["sentiment_score"] = float(score_match.group(1))
        except ValueError:
            pass

    # 检测情绪关键词
    if any(kw in report for kw in ["恐慌", "极度悲观", "抛售", "恐惧"]):
        result["rating"] = "极度悲观（逆向买入信号）"
        result["core_finding"] = "市场恐慌，可能是逆向买入机会"
    elif any(kw in report for kw in ["狂热", "极度乐观", "疯狂", "贪婪"]):
        result["rating"] = "极度乐观（逆向卖出信号）"
        result["core_finding"] = "市场过热，注意风险"
    elif any(kw in report for kw in ["悲观", "谨慎", "担忧"]):
        result["rating"] = "偏悲观"
        result["core_finding"] = "市场情绪偏悲观"
    elif any(kw in report for kw in ["乐观", "看好", "积极"]):
        result["rating"] = "偏乐观"
        result["core_finding"] = "市场情绪偏乐观"
    else:
        result["rating"] = "中性"
        result["core_finding"] = "市场情绪中性"

    return result


def format_analyst_ratings_summary(
    market_report: str,
    fundamentals_report: str,
    news_report: str,
    sentiment_report: str
) -> str:
    """
    格式化所有分析师评级汇总

    Args:
        market_report: 技术面报告
        fundamentals_report: 基本面报告
        news_report: 消息面报告
        sentiment_report: 情绪面报告

    Returns:
        格式化的评级汇总文本
    """
    market_rating = extract_rating_from_market_report(market_report)
    fundamentals_rating = extract_rating_from_fundamentals_report(fundamentals_report)
    news_rating = extract_sentiment_from_news_report(news_report)
    sentiment_rating = extract_sentiment_from_sentiment_report(sentiment_report)

    summary = f"""**分析师报告核心结论**：

| 分析师 | 评级 | 核心发现 |
|--------|------|----------|
| 技术面 | {market_rating['rating']} | {market_rating.get('core_finding', '无')} |
| 基本面 | {fundamentals_rating['rating']} | {fundamentals_rating.get('core_finding', '无')} |
| 消息面 | {news_rating['rating']} | {news_rating.get('core_finding', '无')} |
| 情绪面 | {sentiment_rating['rating']} | {sentiment_rating.get('core_finding', '无')} |
"""

    # 统计买入/卖出信号
    buy_count = sum(1 for r in [market_rating, fundamentals_rating, news_rating, sentiment_rating]
                   if "买入" in r.get('rating', '') or "看多" in r.get('rating', ''))
    sell_count = sum(1 for r in [market_rating, fundamentals_rating, news_rating, sentiment_rating]
                    if "卖出" in r.get('rating', '') or "看空" in r.get('rating', ''))

    summary += f"\n**信号统计**：看多{buy_count}个，看空{sell_count}个"

    return summary


def extract_key_metrics_from_fundamentals(report: str) -> Dict[str, Any]:
    """
    从基本面报告中提取空方必须回应的关键指标

    Args:
        report: 基本面分析报告文本

    Returns:
        关键指标字典
    """
    metrics = {
        "risk_reward_ratio": None,
        "safety_margin": None,
        "target_price": None,
        "pe_range": None,
        "pb_range": None,
    }

    if not report:
        return metrics

    # 提取盈亏比
    ratio_match = re.search(r'盈亏比[：:\s]*([\d.]+)', report)
    if ratio_match:
        try:
            metrics["risk_reward_ratio"] = float(ratio_match.group(1))
        except ValueError:
            pass

    # 检查极佳情况
    if "极佳" in report:
        metrics["risk_reward_ratio"] = "极佳"

    # 提取安全边际
    margin_match = re.search(r'安全边际[：:\s]*([\d.]+)%?', report)
    if margin_match:
        try:
            metrics["safety_margin"] = float(margin_match.group(1))
        except ValueError:
            pass

    # 提取目标价
    target_match = re.search(r'目标价[：:\s]*([\d.]+)', report)
    if target_match:
        try:
            metrics["target_price"] = float(target_match.group(1))
        except ValueError:
            pass

    # 提取PE区间
    pe_match = re.search(r'PE[估值区间]*[：:\s]*\[?([\d.]+)[~-]([\d.]+)\]?', report)
    if pe_match:
        try:
            metrics["pe_range"] = [float(pe_match.group(1)), float(pe_match.group(2))]
        except ValueError:
            pass

    return metrics


def format_key_metrics_for_bear(report: str) -> str:
    """
    格式化基本面关键指标，供空方分析师回应

    Args:
        report: 基本面分析报告文本

    Returns:
        格式化的关键指标文本
    """
    metrics = extract_key_metrics_from_fundamentals(report)

    lines = ["**基本面报告核心发现（空方必须回应）**："]

    if metrics["risk_reward_ratio"]:
        lines.append(f"- 盈亏比：{metrics['risk_reward_ratio']}")

    if metrics["safety_margin"]:
        lines.append(f"- 安全边际：{metrics['safety_margin']}%")

    if metrics["target_price"]:
        lines.append(f"- 目标价：{metrics['target_price']}元")

    if metrics["pe_range"]:
        lines.append(f"- PE估值区间：{metrics['pe_range'][0]}-{metrics['pe_range'][1]}倍")

    if len(lines) == 1:
        lines.append("- 无明确量化指标")

    return "\n".join(lines)
