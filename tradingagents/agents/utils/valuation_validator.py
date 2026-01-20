"""
估值报告验证模块

提供:
1. PE/PB区间合理性验证
2. EPS/PE数学一致性校验
3. PB交叉验证差异分析
4. 股息率交叉验证（高股息股票）
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


def extract_valuation_decision(report: str) -> Optional[Dict[str, Any]]:
    """
    从基本面分析报告中提取JSON估值决策块

    Args:
        report: 基本面分析报告文本

    Returns:
        估值决策字典，提取失败返回None
    """
    if not report:
        return None

    # 尝试匹配JSON块
    patterns = [
        r'\{[^{}]*"valuation_decision"[^{}]*\{[^{}]*\}[^{}]*\}',
        r'"valuation_decision"\s*:\s*\{([^}]+)\}',
    ]

    for pattern in patterns:
        match = re.search(pattern, report, re.DOTALL)
        if match:
            try:
                json_str = match.group(0)
                # 如果匹配的是内部块，包装成完整JSON
                if not json_str.startswith('{'):
                    json_str = '{"valuation_decision": {' + match.group(1) + '}}'
                data = json.loads(json_str)
                return data.get("valuation_decision", data)
            except json.JSONDecodeError:
                continue

    # 尝试提取关键字段
    decision = {}

    # 提取目标倍数区间
    range_match = re.search(r'target_multiple_range["\s:]+\[?\s*(\d+\.?\d*)\s*[,\-]\s*(\d+\.?\d*)', report)
    if range_match:
        decision["target_multiple_range"] = [float(range_match.group(1)), float(range_match.group(2))]

    # 提取当前倍数
    current_match = re.search(r'current_multiple["\s:]+(\d+\.?\d*)', report)
    if current_match:
        decision["current_multiple"] = float(current_match.group(1))

    # 提取基础EPS/BVPS
    eps_match = re.search(r'base_eps_or_bvps["\s:]+(\d+\.?\d*)', report)
    if eps_match:
        decision["base_eps_or_bvps"] = float(eps_match.group(1))

    return decision if decision else None


def extract_target_price(report: str) -> Optional[float]:
    """
    从报告中提取目标价

    Args:
        report: 报告文本

    Returns:
        目标价，提取失败返回None
    """
    patterns = [
        r'目标价[：:\s]*(\d+\.?\d*)\s*元',
        r'加权目标价[：:\s]*(\d+\.?\d*)',
        r'target.*?price[：:\s]*(\d+\.?\d*)',
    ]

    for pattern in patterns:
        match = re.search(pattern, report, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None


def validate_valuation_report(
    fundamentals_report: str,
    current_price: float,
    daily_basic_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    验证估值报告数据一致性

    Args:
        fundamentals_report: 基本面分析报告文本
        current_price: 当前股价
        daily_basic_data: 每日估值数据，包含:
            - pe_min: 历史PE最小值
            - pe_25: PE 25%分位
            - pe_median: PE中位数
            - pe_75: PE 75%分位
            - pe_max: 历史PE最大值
            - pb_min, pb_25, pb_median, pb_75, pb_max: PB对应值
            - bps: 每股净资产
            - eps: 每股收益

    Returns:
        {
            "passed": bool,
            "warnings": list[str],
            "details": dict
        }
    """
    warnings = []
    details = {}

    if not fundamentals_report or not daily_basic_data:
        return {
            "passed": True,
            "warnings": ["数据不足，无法执行估值验证"],
            "details": {}
        }

    # 1. 提取JSON估值决策块
    decision = extract_valuation_decision(fundamentals_report)
    details["valuation_decision"] = decision

    # 2. 验证PE区间是否≥历史最小值
    pe_min = daily_basic_data.get("pe_min")
    if decision and pe_min:
        pe_range = decision.get("target_multiple_range", [])
        if pe_range and len(pe_range) >= 1:
            if pe_range[0] < pe_min:
                warnings.append(
                    f"⚠️ PE区间下限({pe_range[0]:.1f}倍)低于历史最小值({pe_min:.1f}倍)，"
                    f"等于假设市场给出史无前例的低估值"
                )
                details["pe_range_violation"] = {
                    "reported_min": pe_range[0],
                    "historical_min": pe_min
                }

    # 3. 验证 股价/EPS ≈ 当前PE（误差≤5%建议使用计算值，>10%警告）
    eps = daily_basic_data.get("eps") or (decision.get("base_eps_or_bvps") if decision else None)
    reported_pe = decision.get("current_multiple") if decision else None
    tushare_pe = daily_basic_data.get("current_pe")  # Tushare提供的PE

    if eps and current_price and eps > 0:
        calculated_pe = current_price / eps

        details["pe_consistency"] = {
            "current_price": current_price,
            "eps": eps,
            "eps_source": "报告提取",
            "calculated_pe": round(calculated_pe, 2),
            "reported_pe": reported_pe,
            "tushare_pe": tushare_pe,
        }

        # 与报告标注的PE对比
        if reported_pe and reported_pe > 0:
            error_vs_reported = abs(calculated_pe - reported_pe) / reported_pe
            details["pe_consistency"]["error_vs_reported_pct"] = round(error_vs_reported * 100, 1)

            if error_vs_reported > 0.1:
                warnings.append(
                    f"⚠️ PE数学矛盾：股价{current_price}元 ÷ EPS{eps}元 = {calculated_pe:.1f}倍，"
                    f"但报告标注{reported_pe}倍（误差{error_vs_reported*100:.0f}%），建议使用计算值"
                )
                details["pe_consistency"]["recommended_pe"] = round(calculated_pe, 2)
            elif error_vs_reported > 0.05:
                # 误差5%-10%，记录但不警告，建议使用计算值
                details["pe_consistency"]["recommended_pe"] = round(calculated_pe, 2)
                details["pe_consistency"]["note"] = f"PE差异{error_vs_reported*100:.0f}%>5%，已建议使用计算值"

        # 与Tushare PE对比（辅助验证）
        if tushare_pe and tushare_pe > 0:
            error_vs_tushare = abs(calculated_pe - tushare_pe) / tushare_pe
            details["pe_consistency"]["error_vs_tushare_pct"] = round(error_vs_tushare * 100, 1)
            if error_vs_tushare > 0.05:
                details["pe_consistency"]["tushare_note"] = (
                    f"自行计算PE({calculated_pe:.1f})与Tushare PE({tushare_pe:.1f})差异"
                    f"{error_vs_tushare*100:.0f}%，可能存在EPS口径差异（TTM vs 季度）"
                )

    # 4. PB交叉验证
    bps = daily_basic_data.get("bps")
    pb_median = daily_basic_data.get("pb_median")
    pe_target = extract_target_price(fundamentals_report)

    if bps and pb_median and bps > 0 and pb_median > 0:
        pb_target = bps * pb_median

        details["pb_cross_validation"] = {
            "bps": bps,
            "pb_median": pb_median,
            "pb_target_price": round(pb_target, 2)
        }

        if pe_target and current_price > 0:
            pe_upside = (pe_target - current_price) / current_price * 100
            pb_upside = (pb_target - current_price) / current_price * 100
            diff_pct = abs(pe_upside - pb_upside)

            details["pb_cross_validation"].update({
                "pe_target_price": pe_target,
                "pe_upside_pct": round(pe_upside, 1),
                "pb_upside_pct": round(pb_upside, 1),
                "diff_pct": round(diff_pct, 1)
            })

            if diff_pct > 30:
                warnings.append(
                    f"⚠️ 估值重大分歧：PE目标价{pe_target:.2f}元(较现价{pe_upside:+.0f}%) vs "
                    f"PB目标价{pb_target:.2f}元(较现价{pb_upside:+.0f}%)，差异{diff_pct:.0f}个百分点"
                )

    return {
        "passed": len(warnings) == 0,
        "warnings": warnings,
        "details": details
    }


def extract_daily_basic_from_report(report: str) -> Dict[str, Any]:
    """
    从基本面报告中提取估值统计数据（表5格式）

    Args:
        report: 基本面分析报告文本

    Returns:
        包含PE/PB历史统计的字典
    """
    data = {}

    # 尝试提取PE相关数据
    pe_patterns = {
        "pe_min": r'PE[^|]*\|[^|]*(\d+\.?\d*)[^|]*\|',  # 历史最小
        "pe_25": r'PE[^|]*\|[^|]*\d+\.?\d*[^|]*\|[^|]*(\d+\.?\d*)',  # 25%分位
        "pe_median": r'PE[^|]*中位数[：:\s]*(\d+\.?\d*)',
        "pe_75": r'PE[^|]*75%[分位]*[：:\s]*(\d+\.?\d*)',
        "pe_max": r'PE[^|]*最大[值]?[：:\s]*(\d+\.?\d*)',
    }

    # 尝试从表格中提取PE行数据
    pe_row_match = re.search(
        r'\|\s*PE\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)',
        report
    )
    if pe_row_match:
        data["pe_min"] = float(pe_row_match.group(1))
        data["pe_25"] = float(pe_row_match.group(2))
        data["pe_median"] = float(pe_row_match.group(3))
        data["pe_75"] = float(pe_row_match.group(4))
        data["pe_max"] = float(pe_row_match.group(5))

    # 尝试从表格中提取PB行数据
    pb_row_match = re.search(
        r'\|\s*PB\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)\s*\|\s*(\d+\.?\d*)',
        report
    )
    if pb_row_match:
        data["pb_min"] = float(pb_row_match.group(1))
        data["pb_25"] = float(pb_row_match.group(2))
        data["pb_median"] = float(pb_row_match.group(3))
        data["pb_75"] = float(pb_row_match.group(4))
        data["pb_max"] = float(pb_row_match.group(5))

    # 提取BPS
    bps_match = re.search(r'每股净资产[（(]?BPS[）)]?[：:\s]*(\d+\.?\d*)', report, re.IGNORECASE)
    if bps_match:
        data["bps"] = float(bps_match.group(1))
    else:
        bps_match = re.search(r'BPS[：:\s]*(\d+\.?\d*)', report)
        if bps_match:
            data["bps"] = float(bps_match.group(1))

    # 提取EPS（优先TTM）
    eps_patterns = [
        r'TTM\s*EPS[：:\s]*(\d+\.?\d*)',
        r'TTM每股收益[：:\s]*(\d+\.?\d*)',
        r'每股收益[（(]?EPS[）)]?[：:\s]*(\d+\.?\d*)',
        r'EPS[：:\s]*(\d+\.?\d*)',
    ]
    for pattern in eps_patterns:
        eps_match = re.search(pattern, report, re.IGNORECASE)
        if eps_match:
            data["eps"] = float(eps_match.group(1))
            break

    # 提取当前PE（从表格或正文）
    current_pe_patterns = [
        r'当前[PE值]?[：:\s]*(\d+\.?\d*)[倍]?',
        r'\|\s*PE\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*(\d+\.?\d*)',  # 表格当前值列
        r'PE\(TTM\)[：:\s]*(\d+\.?\d*)',
    ]
    for pattern in current_pe_patterns:
        pe_match = re.search(pattern, report)
        if pe_match:
            data["current_pe"] = float(pe_match.group(1))
            break

    return data


def format_validation_warnings(validation_result: Dict[str, Any]) -> str:
    """
    将验证结果格式化为Markdown警告文本

    Args:
        validation_result: validate_valuation_report返回的结果

    Returns:
        格式化的警告文本，如果验证通过返回空字符串
    """
    if validation_result.get("passed", True):
        return ""

    warnings = validation_result.get("warnings", [])
    if not warnings:
        return ""

    lines = [
        "## ⚠️ 数据一致性警告\n",
        "以下问题在自动验证中被检测到，请人工复核：\n"
    ]

    for i, warning in enumerate(warnings, 1):
        lines.append(f"{i}. {warning}")

    lines.append("\n---\n")

    return "\n".join(lines)


# ===== 股息率估值验证模块 =====

# 高股息行业列表
HIGH_DIVIDEND_INDUSTRIES = [
    "公用事业", "电力", "水务", "燃气",
    "银行", "金融",
    "高速公路", "港口", "机场",
    "地产", "REIT"
]


def extract_dividend_data(report: str) -> Dict[str, Any]:
    """
    从基本面报告中提取分红和股息率数据

    Args:
        report: 基本面分析报告文本

    Returns:
        包含分红相关数据的字典
    """
    data = {}

    # 提取近1年每股分红
    recent_div_match = re.search(r'近1年每股分红[：:\s]*(\d+\.?\d*)', report)
    if recent_div_match:
        data["recent_dividend"] = float(recent_div_match.group(1))

    # 提取近3年平均分红
    avg_div_match = re.search(r'近3年平均分红[：:\s]*(\d+\.?\d*)', report)
    if avg_div_match:
        data["avg_3y_dividend"] = float(avg_div_match.group(1))

    # 提取当前股息率
    yield_patterns = [
        r'当前股息率[：:\s]*(\d+\.?\d*)%',
        r'股息率[：:\s]*(\d+\.?\d*)%',
    ]
    for pattern in yield_patterns:
        yield_match = re.search(pattern, report)
        if yield_match:
            data["current_yield_pct"] = float(yield_match.group(1))
            break

    # 尝试从valuation_decision JSON中提取
    decision = extract_valuation_decision(report)
    if decision:
        div_validation = decision.get("dividend_yield_validation", {})
        if div_validation:
            for key in ["recent_dividend", "avg_3y_dividend", "current_yield_pct",
                        "target_yield_range", "dividend_target_price"]:
                if key in div_validation and div_validation[key] is not None:
                    data[key] = div_validation[key]

    return data


def is_high_dividend_stock(
    fundamentals_report: str,
    current_yield_threshold: float = 3.0
) -> bool:
    """
    判断是否为高股息股票（需要进行股息率验证）

    触发条件（满足任一）：
    1. 行业类型属于高股息行业
    2. 当前股息率 > threshold（默认3%）

    Args:
        fundamentals_report: 基本面分析报告文本
        current_yield_threshold: 股息率阈值，默认3%

    Returns:
        是否为高股息股票
    """
    if not fundamentals_report:
        return False

    # 1. 检查行业类型
    decision = extract_valuation_decision(fundamentals_report)
    if decision:
        industry_type = decision.get("industry_type", "")
        for high_div_industry in HIGH_DIVIDEND_INDUSTRIES:
            if high_div_industry in industry_type:
                return True

        # 检查是否已在JSON中标记启用
        div_validation = decision.get("dividend_yield_validation", {})
        if div_validation.get("enabled"):
            return True

    # 2. 检查当前股息率
    div_data = extract_dividend_data(fundamentals_report)
    current_yield = div_data.get("current_yield_pct", 0)
    if current_yield > current_yield_threshold:
        return True

    # 3. 正文中检查行业关键词
    for industry in HIGH_DIVIDEND_INDUSTRIES:
        if industry in fundamentals_report[:500]:  # 只检查报告开头
            return True

    return False


def validate_dividend_yield(
    fundamentals_report: str,
    current_price: float,
    primary_target_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    验证股息率估值数据一致性

    检查项：
    1. 报告股息率 vs 计算股息率（误差≤15%）
    2. 股息率目标价 vs 主要估值目标价差异（>30%警告）
    3. 分红可持续性提示

    Args:
        fundamentals_report: 基本面分析报告文本
        current_price: 当前股价
        primary_target_price: 主要估值方法得出的目标价（可选）

    Returns:
        {
            "passed": bool,
            "warnings": list[str],
            "details": dict,
            "applicable": bool  # 是否适用股息率验证
        }
    """
    warnings = []
    details = {}

    # 检查是否适用
    if not is_high_dividend_stock(fundamentals_report):
        return {
            "passed": True,
            "warnings": [],
            "details": {},
            "applicable": False
        }

    details["applicable"] = True

    # 提取分红数据
    div_data = extract_dividend_data(fundamentals_report)
    details["extracted_data"] = div_data

    recent_div = div_data.get("recent_dividend", 0)
    reported_yield = div_data.get("current_yield_pct", 0)

    # 1. 验证股息率计算一致性
    if recent_div > 0 and current_price > 0:
        calculated_yield = (recent_div / current_price) * 100
        details["calculated_yield_pct"] = round(calculated_yield, 2)

        if reported_yield > 0:
            error = abs(calculated_yield - reported_yield) / reported_yield
            details["yield_error_pct"] = round(error * 100, 1)

            if error > 0.15:
                warnings.append(
                    f"⚠️ 股息率矛盾：分红{recent_div}元 ÷ 股价{current_price}元 = "
                    f"{calculated_yield:.2f}%，但报告标注{reported_yield:.2f}%（误差{error*100:.0f}%）"
                )

    # 2. 股息率目标价 vs 主要估值目标价交叉验证
    div_target = div_data.get("dividend_target_price")
    if div_target is None and recent_div > 0:
        # 尝试从报告中提取股息率目标价
        div_target_match = re.search(r'股息率[^目]*目标价[：:\s]*(\d+\.?\d*)', fundamentals_report)
        if div_target_match:
            div_target = float(div_target_match.group(1))
        else:
            # 用中位数股息率估算（假设3.5%）
            div_target = recent_div / 0.035

    if div_target and current_price > 0:
        details["dividend_target_price"] = round(div_target, 2)
        div_upside = (div_target - current_price) / current_price * 100
        details["dividend_upside_pct"] = round(div_upside, 1)

        # 提取主要估值目标价
        if primary_target_price is None:
            primary_target_price = extract_target_price(fundamentals_report)

        if primary_target_price and primary_target_price > 0:
            primary_upside = (primary_target_price - current_price) / current_price * 100
            diff_pct = abs(div_upside - primary_upside)

            details["primary_target_price"] = primary_target_price
            details["primary_upside_pct"] = round(primary_upside, 1)
            details["yield_vs_primary_diff_pct"] = round(diff_pct, 1)

            if diff_pct > 30:
                warnings.append(
                    f"⚠️ 股息率vs主要估值分歧：股息率目标价{div_target:.2f}元（{div_upside:+.0f}%）vs "
                    f"主要估值目标价{primary_target_price:.2f}元（{primary_upside:+.0f}%），"
                    f"差异{diff_pct:.0f}个百分点"
                )

    # 3. 无分红数据警告
    if recent_div <= 0 and is_high_dividend_stock(fundamentals_report, 0):
        warnings.append(
            "⚠️ 高股息行业但无有效分红数据，股息率验证无法执行"
        )

    return {
        "passed": len(warnings) == 0,
        "warnings": warnings,
        "details": details,
        "applicable": True
    }


def validate_dividend_table_presence(
    fundamentals_report: str,
    is_high_dividend: bool = None
) -> Dict[str, Any]:
    """
    验证高股息股票是否包含完整股息率估值表格

    检查项：
    1. 三情景估值表格（悲观/中性/乐观）
    2. 加权目标价
    3. TTM分红明细
    4. 股息率区间来源标注

    Args:
        fundamentals_report: 基本面分析报告文本
        is_high_dividend: 是否为高股息股票（若None则自动判断）

    Returns:
        {
            "passed": bool,
            "warnings": list[str],
            "details": dict,
            "applicable": bool
        }
    """
    warnings = []
    details = {
        "has_scenario_table": False,
        "has_weighted_price": False,
        "has_ttm_details": False,
        "has_yield_source": False
    }

    # 自动判断是否为高股息股票
    if is_high_dividend is None:
        is_high_dividend = is_high_dividend_stock(fundamentals_report)

    if not is_high_dividend:
        return {
            "passed": True,
            "warnings": [],
            "details": details,
            "applicable": False
        }

    # 1. 检查三情景估值表格
    has_pessimistic = "悲观" in fundamentals_report and "目标" in fundamentals_report
    has_neutral = "中性" in fundamentals_report
    has_optimistic = "乐观" in fundamentals_report

    # 检查是否有股息率估值表格格式
    has_table_format = (
        ("| 悲观 |" in fundamentals_report or "| 情景 |" in fundamentals_report) and
        "目标股息率" in fundamentals_report
    )

    details["has_scenario_table"] = has_pessimistic and has_neutral and has_optimistic and has_table_format

    if not details["has_scenario_table"]:
        warnings.append(
            "⚠️ 高股息股票缺少完整的股息率估值三情景表格，"
            "请展开计算悲观/中性/乐观情景的目标价"
        )

    # 2. 检查加权目标价
    has_weighted = "加权" in fundamentals_report and "元" in fundamentals_report
    details["has_weighted_price"] = has_weighted

    if not has_weighted:
        warnings.append(
            "⚠️ 股息率估值缺少加权目标价（25%/50%/25%权重）"
        )

    # 3. 检查TTM分红明细（多次分红股票）
    # 搜索"分红明细"或"TTM分红"
    has_ttm_details = (
        "TTM分红" in fundamentals_report or
        "分红明细" in fundamentals_report or
        "近12个月累计" in fundamentals_report
    )
    details["has_ttm_details"] = has_ttm_details

    # 检查是否只取了单次分红而非累计
    single_div_warning = False
    if "近1年每股分红" in fundamentals_report and "分红次数" not in fundamentals_report:
        # 检查是否有多次分红迹象但未说明
        div_match = re.search(r'近1年每股分红[（(TTM)）]?[：:\s]*(\d+\.?\d*)', fundamentals_report)
        if div_match:
            single_div = float(div_match.group(1))
            # 如果分红金额较小（<1元）且是煤炭/银行等高分红行业，可能是单次分红
            if single_div < 1.0:
                industry_keywords = ["煤炭", "银行", "神华", "中国银行", "工商银行"]
                for kw in industry_keywords:
                    if kw in fundamentals_report[:500]:
                        single_div_warning = True
                        break

    if single_div_warning:
        warnings.append(
            "⚠️ TTM分红可能只取了单次分红，"
            "煤炭/银行等行业通常每年分红2-3次，请核实是否累加"
        )

    # 4. 检查股息率区间来源标注
    has_source = (
        "历史分位" in fundamentals_report or
        "行业经验值" in fundamentals_report or
        "置信度" in fundamentals_report or
        "数据来源" in fundamentals_report
    )
    details["has_yield_source"] = has_source

    if not has_source:
        warnings.append(
            "⚠️ 股息率目标区间未标注来源（历史分位/行业经验值）"
        )

    return {
        "passed": len(warnings) == 0,
        "warnings": warnings,
        "details": details,
        "applicable": True
    }
