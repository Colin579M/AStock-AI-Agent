"""
状态管理工具模块

提供:
1. 历史记录摘要功能 - 防止context window耗尽
2. 状态验证工具
3. 滚动窗口管理
"""

import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# 配置常量
MAX_HISTORY_CHARS = 8000  # 历史记录最大字符数（约4000 tokens）
KEEP_RECENT_CHARS = 3000  # 保留最近的字符数
SUMMARY_PREFIX = "[历史摘要]\n"


def summarize_history(
    history: str,
    summarizer: Optional[Callable[[str], str]] = None,
    max_chars: int = MAX_HISTORY_CHARS,
    keep_recent: int = KEEP_RECENT_CHARS
) -> str:
    """
    对过长的历史记录进行摘要

    当历史记录超过max_chars时，将较早的内容摘要化，只保留最近的keep_recent字符。

    Args:
        history: 原始历史记录字符串
        summarizer: 可选的LLM摘要函数，如果不提供则使用简单截断
        max_chars: 触发摘要的最大字符数
        keep_recent: 保留最近内容的字符数

    Returns:
        str: 处理后的历史记录
    """
    if not history or len(history) <= max_chars:
        return history

    logger.info(f"History exceeds {max_chars} chars ({len(history)}), applying summarization")

    # 分割历史记录：保留最近的部分，摘要较早的部分
    split_point = len(history) - keep_recent
    old_content = history[:split_point]
    recent_content = history[split_point:]

    # 如果有LLM摘要器，使用它；否则使用简单截断
    if summarizer:
        try:
            summary = summarizer(old_content)
            summarized_history = f"{SUMMARY_PREFIX}{summary}\n\n[最近对话]\n{recent_content}"
        except Exception as e:
            logger.warning(f"LLM summarization failed, using truncation: {e}")
            summarized_history = _simple_truncate(old_content, recent_content)
    else:
        summarized_history = _simple_truncate(old_content, recent_content)

    logger.info(f"History reduced from {len(history)} to {len(summarized_history)} chars")
    return summarized_history


def _simple_truncate(old_content: str, recent_content: str) -> str:
    """
    简单截断策略：提取关键要点

    从旧内容中提取主要观点，而非完整保留。
    """
    # 尝试从旧内容中提取关键句子（每个发言者的最后一句）
    lines = old_content.strip().split('\n')
    key_points = []

    current_speaker = None
    last_line = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测发言者
        if line.startswith("Bull ") or "Bull" in line[:20]:
            if current_speaker and last_line:
                key_points.append(f"- Bull观点: {_extract_key_point(last_line)}")
            current_speaker = "Bull"
            last_line = line
        elif line.startswith("Bear ") or "Bear" in line[:20]:
            if current_speaker and last_line:
                key_points.append(f"- Bear观点: {_extract_key_point(last_line)}")
            current_speaker = "Bear"
            last_line = line
        elif line.startswith("Risky ") or line.startswith("Aggressive"):
            if current_speaker and last_line:
                key_points.append(f"- 激进观点: {_extract_key_point(last_line)}")
            current_speaker = "Risky"
            last_line = line
        elif line.startswith("Safe ") or line.startswith("Conservative"):
            if current_speaker and last_line:
                key_points.append(f"- 保守观点: {_extract_key_point(last_line)}")
            current_speaker = "Safe"
            last_line = line
        elif line.startswith("Neutral"):
            if current_speaker and last_line:
                key_points.append(f"- 中立观点: {_extract_key_point(last_line)}")
            current_speaker = "Neutral"
            last_line = line
        else:
            last_line = line

    # 添加最后一个发言者的观点
    if current_speaker and last_line:
        speaker_name = {
            "Bull": "Bull", "Bear": "Bear",
            "Risky": "激进", "Safe": "保守", "Neutral": "中立"
        }.get(current_speaker, current_speaker)
        key_points.append(f"- {speaker_name}观点: {_extract_key_point(last_line)}")

    # 如果没有提取到任何关键点，使用简单截断
    if not key_points:
        # 保留开头300字符作为摘要
        summary = old_content[:300] + "..." if len(old_content) > 300 else old_content
        return f"{SUMMARY_PREFIX}{summary}\n\n[最近对话]\n{recent_content}"

    summary = "\n".join(key_points[-5:])  # 最多保留5个关键点
    return f"{SUMMARY_PREFIX}{summary}\n\n[最近对话]\n{recent_content}"


def _extract_key_point(text: str, max_length: int = 150) -> str:
    """
    从文本中提取关键要点

    优先保留结论性语句。
    """
    # 移除发言者标识
    for prefix in ["Bull Analyst:", "Bear Analyst:", "Risky Analyst:",
                   "Safe Analyst:", "Neutral Analyst:", "激进方:", "保守方:", "中立方:"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    # 如果文本足够短，直接返回
    if len(text) <= max_length:
        return text

    # 尝试找到结论性语句（通常在末尾）
    sentences = text.replace('。', '.').replace('；', ';').split('.')
    sentences = [s.strip() for s in sentences if s.strip()]

    if sentences:
        # 取最后1-2个句子作为关键点
        key_sentences = sentences[-2:] if len(sentences) >= 2 else sentences
        result = '. '.join(key_sentences)
        if len(result) > max_length:
            result = result[:max_length] + "..."
        return result

    return text[:max_length] + "..."


def create_llm_summarizer(llm) -> Callable[[str], str]:
    """
    创建基于LLM的历史摘要器

    Args:
        llm: LangChain LLM实例

    Returns:
        Callable: 摘要函数
    """
    def summarize(content: str) -> str:
        prompt = f"""请将以下辩论历史摘要为3-5个要点，保留核心观点和关键数据：

{content}

摘要要求：
1. 每个要点用一句话概括
2. 保留关键数据和百分比
3. 标注观点来源（Bull/Bear/激进/保守/中立）
4. 用中文输出"""

        response = llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    return summarize


def validate_debate_state(state: Dict[str, Any], state_type: str = "invest") -> bool:
    """
    验证辩论状态的完整性

    Args:
        state: 辩论状态字典
        state_type: "invest" 或 "risk"

    Returns:
        bool: 状态是否有效
    """
    if state_type == "invest":
        required_keys = ["history", "current_response", "count"]
    elif state_type == "risk":
        required_keys = ["history", "current_risky_response",
                        "current_safe_response", "current_neutral_response", "count"]
    else:
        logger.warning(f"Unknown state type: {state_type}")
        return False

    for key in required_keys:
        if key not in state:
            logger.warning(f"Missing key in {state_type} state: {key}")
            return False

    return True


def apply_history_limits(
    debate_state: Dict[str, Any],
    history_keys: list,
    summarizer: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """
    对辩论状态中的所有历史字段应用长度限制

    Args:
        debate_state: 辩论状态字典
        history_keys: 需要检查的历史字段列表
        summarizer: 可选的LLM摘要器

    Returns:
        Dict: 处理后的辩论状态
    """
    result = debate_state.copy()

    for key in history_keys:
        if key in result and isinstance(result[key], str):
            original_len = len(result[key])
            result[key] = summarize_history(result[key], summarizer)
            if len(result[key]) < original_len:
                logger.debug(f"Summarized {key}: {original_len} -> {len(result[key])} chars")

    return result


# 便捷函数：为投资辩论状态应用限制
def apply_invest_debate_limits(
    state: Dict[str, Any],
    summarizer: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """对投资辩论状态应用历史长度限制"""
    return apply_history_limits(
        state,
        ["history", "bull_history", "bear_history"],
        summarizer
    )


# 便捷函数：为风险辩论状态应用限制
def apply_risk_debate_limits(
    state: Dict[str, Any],
    summarizer: Optional[Callable[[str], str]] = None
) -> Dict[str, Any]:
    """对风险辩论状态应用历史长度限制"""
    return apply_history_limits(
        state,
        ["history", "risky_history", "safe_history", "neutral_history"],
        summarizer
    )
