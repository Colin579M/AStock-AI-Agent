"""
概念关联度验证数据获取工具

数据来源:
1. 互动易/e互动 - 投资者问答（深交所/上交所）
2. 公司公告 - 巨潮资讯信息披露
3. 概念板块 - Tushare概念成分

功能:
- 追溯概念炒作起点
- 验证概念关联的实质性
- 输出关联度评分和证据链
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re
import logging

from .retry_utils import retry_with_backoff, safe_api_call

logger = logging.getLogger(__name__)

# ============================================================================
# 热门概念关键词配置
# ============================================================================

CONCEPT_KEYWORDS = {
    "商业航天": ["航天", "卫星", "火箭", "发射", "空天", "太空", "航空航天", "宇航", "星座", "轨道"],
    "低空经济": ["低空", "无人机", "eVTOL", "飞行汽车", "通用航空", "空中交通"],
    "人工智能": ["人工智能", "AI", "大模型", "GPT", "算力", "机器学习", "深度学习", "AIGC"],
    "芯片半导体": ["芯片", "半导体", "集成电路", "晶圆", "封测", "光刻", "制程", "EDA"],
    "新能源": ["锂电", "光伏", "储能", "风电", "氢能", "新能源", "电池", "充电桩"],
    "机器人": ["机器人", "人形机器人", "工业机器人", "减速器", "伺服", "控制器"],
    "量子计算": ["量子", "量子计算", "量子通信", "量子加密"],
    "数据要素": ["数据要素", "数据交易", "数据资产", "数据确权"],
    "华为概念": ["华为", "鸿蒙", "昇腾", "麒麟", "盘古"],
}

# 业务动作关键词（用于公告搜索）
BUSINESS_ACTION_KEYWORDS = [
    "子公司", "战略合作", "投资设立", "业务拓展", "收购", "参股",
    "增资", "合资", "框架协议", "意向协议", "合作备忘录", "签署"
]


# ============================================================================
# 深交所互动易数据获取
# ============================================================================

@retry_with_backoff(max_retries=3, initial_delay=1.0)
def get_investor_qa_szse(stock_code: str, keyword: str = "", max_results: int = 30) -> str:
    """
    获取深交所互动易投资者问答

    Args:
        stock_code: 股票代码（如 002824, 002565）
        keyword: 搜索关键词（可选）
        max_results: 最大返回条数

    Returns:
        格式化的问答数据（Markdown格式）
    """
    try:
        # 确保是6位代码
        stock_code = stock_code.replace(".SZ", "").replace(".SH", "").zfill(6)

        df = ak.stock_irm_cninfo(symbol=stock_code)

        if df is None or df.empty:
            return f"未找到 {stock_code} 的深交所互动易问答数据"

        result = []
        result.append(f"## 深交所互动易问答 ({stock_code})\n")

        # 筛选含关键词的问答
        if keyword:
            keywords = [keyword] if isinstance(keyword, str) else keyword
            mask = df.apply(
                lambda row: any(kw in str(row.get('问题', '')) or kw in str(row.get('回答内容', ''))
                               for kw in keywords),
                axis=1
            )
            df_filtered = df[mask]
            result.append(f"**关键词筛选**: {keyword}\n")
        else:
            df_filtered = df

        if df_filtered.empty:
            result.append(f"未找到包含'{keyword}'的问答记录\n")
            return "\n".join(result)

        total = len(df_filtered)
        df_filtered = df_filtered.head(max_results)
        result.append(f"**共找到 {total} 条相关问答**（显示前{len(df_filtered)}条）\n")

        for idx, row in df_filtered.iterrows():
            question = str(row.get('问题', row.get('提问内容', '')))[:200]
            answer = str(row.get('回答内容', row.get('回复内容', '')))[:300]
            date = str(row.get('提问时间', row.get('更新时间', '')))[:10]

            result.append(f"### Q{idx+1} ({date})")
            result.append(f"**问**: {question}...")
            result.append(f"**答**: {answer}...\n")

        return "\n".join(result)

    except Exception as e:
        logger.error(f"获取深交所互动易数据失败 [{stock_code}]: {e}")
        return f"获取深交所互动易数据失败: {str(e)}"


# ============================================================================
# 上交所e互动数据获取
# ============================================================================

@retry_with_backoff(max_retries=2, initial_delay=2.0)
def get_investor_qa_sse(stock_code: str, keyword: str = "", max_results: int = 20) -> str:
    """
    获取上交所e互动投资者问答

    注意：此接口较慢，需要爬取多页

    Args:
        stock_code: 股票代码（如 601899, 603xxx）
        keyword: 搜索关键词
        max_results: 最大返回条数

    Returns:
        格式化的问答数据
    """
    try:
        stock_code = stock_code.replace(".SH", "").replace(".SZ", "").zfill(6)

        # 上交所e互动接口较慢，设置超时
        df = ak.stock_sns_sseinfo(symbol=stock_code)

        if df is None or df.empty:
            return f"未找到 {stock_code} 的上交所e互动问答数据"

        result = []
        result.append(f"## 上交所e互动问答 ({stock_code})\n")

        # 筛选含关键词的问答
        if keyword:
            mask = df.apply(
                lambda row: keyword in str(row.get('问题', '')) or keyword in str(row.get('回答', '')),
                axis=1
            )
            df_filtered = df[mask]
            result.append(f"**关键词筛选**: {keyword}\n")
        else:
            df_filtered = df

        if df_filtered.empty:
            result.append(f"未找到包含'{keyword}'的问答记录\n")
            return "\n".join(result)

        total = len(df_filtered)
        df_filtered = df_filtered.head(max_results)
        result.append(f"**共找到 {total} 条相关问答**（显示前{len(df_filtered)}条）\n")

        for idx, row in df_filtered.iterrows():
            question = str(row.get('问题', ''))[:200]
            answer = str(row.get('回答', ''))[:300]
            date = str(row.get('日期', ''))[:10]

            result.append(f"### Q{idx+1} ({date})")
            result.append(f"**问**: {question}...")
            result.append(f"**答**: {answer}...\n")

        return "\n".join(result)

    except Exception as e:
        logger.error(f"获取上交所e互动数据失败 [{stock_code}]: {e}")
        return f"获取上交所e互动数据失败: {str(e)}"


def get_investor_qa(stock_code: str, keyword: str = "") -> str:
    """
    统一的投资者问答获取接口

    根据股票代码自动选择深交所互动易或上交所e互动

    Args:
        stock_code: 股票代码
        keyword: 搜索关键词

    Returns:
        格式化的问答数据
    """
    stock_code = stock_code.replace(".SZ", "").replace(".SH", "").zfill(6)

    # 判断交易所：6开头是上交所，0/3开头是深交所
    if stock_code.startswith('6'):
        return get_investor_qa_sse(stock_code, keyword)
    else:
        return get_investor_qa_szse(stock_code, keyword)


# ============================================================================
# 公司公告搜索
# ============================================================================

@retry_with_backoff(max_retries=3, initial_delay=1.0)
def get_announcement_search(
    stock_code: str,
    keyword: str = "",
    days: int = 365
) -> str:
    """
    搜索公司公告（巨潮资讯）

    Args:
        stock_code: 股票代码
        keyword: 搜索关键词（可选）
        days: 查询天数

    Returns:
        格式化的公告列表
    """
    try:
        stock_code = stock_code.replace(".SZ", "").replace(".SH", "").zfill(6)

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        df = ak.stock_zh_a_disclosure_report_cninfo(
            symbol=stock_code,
            market="沪深京",
            keyword="",  # 接口的keyword参数不稳定，后续手动过滤
            category="",
            start_date=start_date,
            end_date=end_date
        )

        if df is None or df.empty:
            return f"未找到 {stock_code} 的公告数据"

        result = []
        result.append(f"## 公司公告搜索 ({stock_code})\n")
        result.append(f"**时间范围**: {start_date} - {end_date}")

        # 手动过滤关键词
        if keyword:
            mask = df['公告标题'].str.contains(keyword, na=False, case=False)
            df_filtered = df[mask]
            result.append(f"**关键词筛选**: {keyword}")
            result.append(f"**匹配公告**: {len(df_filtered)} 条\n")
        else:
            df_filtered = df
            result.append(f"**全部公告**: {len(df_filtered)} 条\n")

        if df_filtered.empty:
            result.append(f"未找到包含'{keyword}'的公告\n")
            return "\n".join(result)

        result.append("| 日期 | 公告标题 |")
        result.append("|------|---------|")

        for _, row in df_filtered.head(20).iterrows():
            title = str(row.get('公告标题', ''))[:60]
            date = str(row.get('公告时间', ''))[:10]
            result.append(f"| {date} | {title} |")

        return "\n".join(result)

    except Exception as e:
        logger.error(f"获取公告数据失败 [{stock_code}]: {e}")
        return f"获取公告数据失败: {str(e)}"


# ============================================================================
# 概念关联度分析
# ============================================================================

def _count_keyword_mentions(text: str, keywords: List[str]) -> int:
    """统计关键词在文本中的出现次数"""
    count = 0
    for kw in keywords:
        count += len(re.findall(re.escape(kw), text, re.IGNORECASE))
    return count


def analyze_concept_relevance(
    stock_code: str,
    target_concept: str
) -> Dict:
    """
    综合分析概念关联度

    Args:
        stock_code: 股票代码
        target_concept: 目标概念（如 "商业航天"）

    Returns:
        概念关联度分析结果字典
    """
    # 获取概念关键词
    keywords = CONCEPT_KEYWORDS.get(target_concept, [target_concept])

    result = {
        "stock_code": stock_code,
        "target_concept": target_concept,
        "keywords": keywords,
        "evidence_sources": [],
        "relevance_score": 0,
        "relevance_level": "",
        "conclusion": ""
    }

    evidence_weight = 0

    # 1. 检查Tushare概念板块
    try:
        from .tushare_utils import get_concept
        concept_data = get_concept(stock_code)

        concept_match = False
        matched_concept = ""
        for kw in keywords:
            if kw in concept_data:
                concept_match = True
                matched_concept = kw
                break

        if concept_match:
            result["evidence_sources"].append({
                "type": "官方概念板块",
                "found": True,
                "weight": 30,
                "description": f"股票属于'{matched_concept}'相关概念板块"
            })
            evidence_weight += 30
        else:
            result["evidence_sources"].append({
                "type": "官方概念板块",
                "found": False,
                "weight": 0,
                "description": "未在官方概念板块中找到直接关联"
            })
    except Exception as e:
        logger.warning(f"获取概念板块失败: {e}")
        result["evidence_sources"].append({
            "type": "官方概念板块",
            "found": False,
            "weight": 0,
            "description": f"数据获取失败: {str(e)[:50]}"
        })

    # 2. 搜索互动易问答
    try:
        qa_data = get_investor_qa(stock_code, keywords[0])

        # 统计关键词出现次数
        qa_mentions = _count_keyword_mentions(qa_data, keywords)

        if qa_mentions > 0:
            qa_weight = min(qa_mentions * 5, 20)  # 每处5分，最多20分
            result["evidence_sources"].append({
                "type": "互动易问答",
                "found": True,
                "weight": qa_weight,
                "count": qa_mentions,
                "description": f"在互动易问答中找到{qa_mentions}处相关提及"
            })
            evidence_weight += qa_weight
        else:
            result["evidence_sources"].append({
                "type": "互动易问答",
                "found": False,
                "weight": 0,
                "description": "互动易问答中未找到相关讨论"
            })
    except Exception as e:
        logger.warning(f"获取互动易数据失败: {e}")
        result["evidence_sources"].append({
            "type": "互动易问答",
            "found": False,
            "weight": 0,
            "description": f"数据获取失败: {str(e)[:50]}"
        })

    # 3. 搜索公告
    try:
        # 搜索关键词相关公告
        announcement_data = get_announcement_search(stock_code, keywords[0], days=365)

        # 检查是否有匹配公告
        if "匹配公告" in announcement_data:
            match = re.search(r'匹配公告.*?(\d+)\s*条', announcement_data)
            if match:
                count = int(match.group(1))
                if count > 0:
                    ann_weight = min(count * 15, 30)  # 每条15分，最多30分
                    result["evidence_sources"].append({
                        "type": "公司公告",
                        "found": True,
                        "weight": ann_weight,
                        "count": count,
                        "description": f"公告中发现{count}条'{keywords[0]}'相关内容"
                    })
                    evidence_weight += ann_weight
                else:
                    result["evidence_sources"].append({
                        "type": "公司公告",
                        "found": False,
                        "weight": 0,
                        "description": "公告中未发现相关业务拓展"
                    })
            else:
                result["evidence_sources"].append({
                    "type": "公司公告",
                    "found": False,
                    "weight": 0,
                    "description": "公告中未发现相关业务拓展"
                })
        else:
            result["evidence_sources"].append({
                "type": "公司公告",
                "found": False,
                "weight": 0,
                "description": "公告中未发现相关业务拓展"
            })
    except Exception as e:
        logger.warning(f"获取公告数据失败: {e}")
        result["evidence_sources"].append({
            "type": "公司公告",
            "found": False,
            "weight": 0,
            "description": f"数据获取失败: {str(e)[:50]}"
        })

    # 4. 搜索业务动作关键词（子公司、战略合作等）
    try:
        for action_kw in ["子公司", "战略合作", "参股"]:
            action_data = get_announcement_search(stock_code, action_kw, days=365)
            if "匹配公告" in action_data:
                match = re.search(r'匹配公告.*?(\d+)\s*条', action_data)
                if match and int(match.group(1)) > 0:
                    # 检查公告内容是否与目标概念相关
                    if any(kw in action_data for kw in keywords):
                        result["evidence_sources"].append({
                            "type": f"业务动作({action_kw})",
                            "found": True,
                            "weight": 15,
                            "description": f"发现与'{target_concept}'相关的{action_kw}公告"
                        })
                        evidence_weight += 15
                        break
    except Exception as e:
        logger.warning(f"搜索业务动作失败: {e}")

    # 5. 计算综合得分和等级
    result["relevance_score"] = min(evidence_weight, 100)

    if evidence_weight >= 50:
        result["relevance_level"] = "有实质业务"
        result["conclusion"] = f"该股票与'{target_concept}'概念有实质关联，存在官方概念板块归属、公告佐证或互动易确认"
    elif evidence_weight >= 20:
        result["relevance_level"] = "有公告提及"
        result["conclusion"] = f"该股票与'{target_concept}'概念有间接关联，互动易或公告中有相关提及，但尚未形成实质业务"
    else:
        result["relevance_level"] = "纯市场联想"
        result["conclusion"] = f"该股票与'{target_concept}'概念关联度较低，可能是市场炒作或投资者联想，需警惕概念炒作风险"

    return result


# ============================================================================
# 综合报告生成
# ============================================================================

def get_concept_validation_report(
    stock_code: str,
    target_concept: str = ""
) -> str:
    """
    生成概念关联度验证报告

    这是对外暴露的主要函数，整合所有数据源生成完整报告

    Args:
        stock_code: 股票代码
        target_concept: 目标概念，如 "商业航天"、"人工智能"

    Returns:
        格式化的概念验证报告（Markdown格式）
    """
    stock_code = stock_code.replace(".SZ", "").replace(".SH", "").zfill(6)

    result = []
    result.append(f"# 概念关联度验证报告\n")
    result.append(f"**股票代码**: {stock_code}")
    result.append(f"**验证概念**: {target_concept}")
    result.append(f"**验证时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # 1. 获取基本信息
    try:
        from .tushare_utils import get_stock_basic_info
        basic_info = get_stock_basic_info(stock_code)
        result.append("## 一、股票基本信息\n")
        result.append(basic_info)
        result.append("")
    except Exception as e:
        result.append(f"## 一、股票基本信息\n\n基本信息获取失败: {e}\n")

    # 2. 获取所属概念板块
    try:
        from .tushare_utils import get_concept
        concept_info = get_concept(stock_code)
        result.append("## 二、所属概念板块（官方）\n")
        result.append(concept_info)
        result.append("")
    except Exception as e:
        result.append(f"## 二、所属概念板块（官方）\n\n概念板块获取失败: {e}\n")

    # 3. 概念关联度分析
    if target_concept:
        result.append(f"## 三、'{target_concept}'概念关联度分析\n")

        analysis = analyze_concept_relevance(stock_code, target_concept)

        # 3.1 证据来源汇总
        result.append("### 3.1 证据来源汇总\n")
        result.append("| 来源 | 是否找到 | 权重 | 说明 |")
        result.append("|------|---------|------|------|")

        for source in analysis["evidence_sources"]:
            found = "✓" if source.get("found") else "✗"
            weight = source.get("weight", 0)
            result.append(f"| {source['type']} | {found} | +{weight} | {source['description']} |")

        # 3.2 关联度评分
        result.append("\n### 3.2 关联度评分\n")

        score = analysis['relevance_score']
        level = analysis['relevance_level']

        # 评分可视化
        bar_filled = int(score / 10)
        bar_empty = 10 - bar_filled
        score_bar = "█" * bar_filled + "░" * bar_empty

        result.append(f"**综合评分**: {score}/100 [{score_bar}]")
        result.append(f"**关联等级**: **{level}**")
        result.append(f"**分析结论**: {analysis['conclusion']}")
        result.append("")

        # 3.3 关联度等级说明
        result.append("### 3.3 关联度等级说明\n")
        result.append("| 等级 | 评分区间 | 特征 | 投资建议 |")
        result.append("|------|---------|------|---------|")
        result.append("| 有实质业务 | 50-100 | 官方概念板块/公告明确提及 | 可关注基本面变化 |")
        result.append("| 有公告提及 | 20-49 | 互动易问答或公告间接提及 | 需谨慎验证实质 |")
        result.append("| 纯市场联想 | 0-19 | 无实质证据支撑 | **警惕炒作风险** |")
        result.append("")

    # 4. 互动易问答摘要
    result.append("## 四、投资者问答摘要\n")
    try:
        if target_concept:
            keywords = CONCEPT_KEYWORDS.get(target_concept, [target_concept])
            qa_data = get_investor_qa(stock_code, keywords[0])
        else:
            qa_data = get_investor_qa(stock_code)

        # 限制输出长度
        if len(qa_data) > 2000:
            qa_data = qa_data[:2000] + "\n\n...(更多问答已省略)"
        result.append(qa_data)
        result.append("")
    except Exception as e:
        result.append(f"问答数据获取失败: {e}\n")

    # 5. 相关公告
    result.append("## 五、近期相关公告\n")
    try:
        if target_concept:
            keywords = CONCEPT_KEYWORDS.get(target_concept, [target_concept])
            ann_data = get_announcement_search(stock_code, keywords[0], days=180)
        else:
            ann_data = get_announcement_search(stock_code, "", days=90)

        result.append(ann_data)
    except Exception as e:
        result.append(f"公告数据获取失败: {e}\n")

    return "\n".join(result)


# ============================================================================
# 导出函数
# ============================================================================

__all__ = [
    "get_investor_qa",
    "get_investor_qa_szse",
    "get_investor_qa_sse",
    "get_announcement_search",
    "analyze_concept_relevance",
    "get_concept_validation_report",
    "CONCEPT_KEYWORDS",
]
