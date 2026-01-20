"""
论点提取器 (Claim Extractor)

从Bull/Bear的回复中提取核心论点，用于锁定反驳机制。

设计原则：
- 规则提取（无LLM调用）：零延迟，适合快速验证
- 未来可扩展为LLM提取以提高准确率
"""

import re
from typing import List, Tuple


def extract_claims_simple(response: str, max_claims: int = 3) -> List[str]:
    """
    规则提取版本（无LLM调用）

    提取规则优先级：
    1. 包含数字的断言（如"PE达200倍"、"渗透率5%"）
    2. 包含判断词的结论句（"因此"、"所以"、"表明"）
    3. 风险/机会关键词句子

    Args:
        response: Bull/Bear的完整回复
        max_claims: 最多提取的论点数量

    Returns:
        核心论点列表（最多max_claims条）
    """
    claims = []
    seen_claims = set()  # 去重

    # 按句子分割（支持中英文标点）
    sentences = re.split(r'[。！？\n;]', response)

    # 清理句子
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    # 规则1：数字断言（最高优先级）
    number_pattern = r'\d+(\.\d+)?[%倍元亿万美元美金]'
    for s in sentences:
        if re.search(number_pattern, s) and s not in seen_claims:
            # 截取合理长度
            claim = s[:200] if len(s) > 200 else s
            claims.append(claim)
            seen_claims.add(s)
            if len(claims) >= max_claims:
                return claims

    # 规则2：结论句（含判断词）
    conclusion_pattern = r'(因此|所以|表明|说明|意味着|可见|综上|由此可见)'
    for s in sentences:
        if re.search(conclusion_pattern, s) and s not in seen_claims:
            claim = s[:200] if len(s) > 200 else s
            claims.append(claim)
            seen_claims.add(s)
            if len(claims) >= max_claims:
                return claims

    # 规则3：风险/机会句
    risk_keywords = r'(风险|压力|下跌|减持|减仓|警惕|注意|泡沫|高估|危险|隐患)'
    opportunity_keywords = r'(机会|潜力|增长|买入|加仓|看好|低估|安全边际|上涨空间)'

    for s in sentences:
        if (re.search(risk_keywords, s) or re.search(opportunity_keywords, s)) and s not in seen_claims:
            claim = s[:200] if len(s) > 200 else s
            claims.append(claim)
            seen_claims.add(s)
            if len(claims) >= max_claims:
                return claims

    return claims[:max_claims]


def mark_claims_addressed(
    pending: List[str],
    response: str,
    threshold: float = 0.4
) -> Tuple[List[str], List[str]]:
    """
    判断哪些pending claims被response回应了

    简单版本：检查claim的关键词是否出现在response中

    Args:
        pending: 待回应的论点列表
        response: 当前回复内容
        threshold: 关键词匹配阈值（0-1）

    Returns:
        (still_pending, newly_addressed) - 仍待回应的论点，新回应的论点
    """
    still_pending = []
    newly_addressed = []

    for claim in pending:
        # 提取claim中的关键数字和中文词汇
        # 数字
        numbers = re.findall(r'\d+(?:\.\d+)?', claim)
        # 中文词汇（2字以上）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', claim)
        # 合并关键词
        keywords = numbers + chinese_words

        if not keywords:
            # 无法提取关键词，保守处理：认为未回应
            still_pending.append(claim)
            continue

        # 计算匹配率
        match_count = sum(1 for kw in keywords if kw in response)
        match_ratio = match_count / len(keywords)

        if match_ratio >= threshold:
            newly_addressed.append(claim)
        else:
            still_pending.append(claim)

    return still_pending, newly_addressed


def format_rebuttal_section(pending_claims: List[str], opponent: str = "对方") -> str:
    """
    格式化必答项区块，用于注入prompt

    Args:
        pending_claims: 待回应的论点列表
        opponent: 对手称呼（"空方"/"多头"）

    Returns:
        格式化的必答项区块（如无待回应论点则返回空字符串）
    """
    if not pending_claims:
        return ""

    claims_text = "\n".join(f"{i+1}. {claim}" for i, claim in enumerate(pending_claims))

    return f"""
═══════════════════════════════════════════════════════════════
【必答项 - 锁定回应】MANDATORY REBUTTAL
═══════════════════════════════════════════════════════════════

{opponent}提出以下论点，你必须逐一回应：

{claims_text}

**回应要求**：
- 承认风险/观点（若合理）并说明应对策略
- 或反驳（必须有数据/逻辑支撑）
- 不得忽略任何一条

⚠️ 未明确回应的论点将被视为你承认其成立。

═══════════════════════════════════════════════════════════════
"""
