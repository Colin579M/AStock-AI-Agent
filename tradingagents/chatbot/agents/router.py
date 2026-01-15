"""
查询路由器

根据用户查询类型，路由到不同的 Agent 处理。
"""
import re
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """查询类型"""
    CHAT = "chat"             # 闲聊（你好、谢谢等）- 直接返回，不调用 LLM
    QUICK = "quick"           # 简单数据查询（价格、涨跌幅、基本信息）
    ANALYSIS = "analysis"     # 需要分析解读（估值分析、技术分析）
    FULL = "full"             # 完整多Agent分析（深度研报）


# 快速查询关键词
QUICK_KEYWORDS = [
    # 价格相关
    "价格", "股价", "多少钱", "什么价", "收盘价", "开盘价",
    "涨跌", "涨幅", "跌幅", "涨了", "跌了",
    "成交量", "成交额", "换手率",
    # 基本信息
    "是什么", "是哪个", "代码是", "叫什么",
    "行业", "板块", "上市", "市值",
    # 简单指标查询
    "PE是", "PB是", "市盈率", "市净率",
    # 资金流向简单查询
    "资金流向", "主力资金", "北向资金",
    # 报告查询
    "历史报告", "之前的报告", "上次分析", "以前的分析",
    "报告列表", "有哪些报告", "查看报告", "看看报告",
    "综合研报", "研报", "分析报告",
]

# 分析类关键词
ANALYSIS_KEYWORDS = [
    # 通用分析
    "分析", "分析一下", "怎么样", "如何",
    # 估值分析
    "估值", "高估", "低估", "便宜", "贵不贵",
    "值不值", "合理", "偏高", "偏低",
    # 趋势分析
    "趋势", "走势", "技术", "形态", "支撑", "压力",
    "均线", "MACD", "KDJ", "RSI",
    # 基本面分析
    "基本面", "财务", "业绩", "盈利", "增长",
    "ROE", "ROA", "毛利率", "净利率",
    # 对比分析
    "对比", "比较", "哪个好", "选哪个",
    # 机构观点
    "机构", "券商", "评级", "目标价",
    # 风险分析
    "风险", "质押", "解禁", "减持",
]

# 完整分析关键词
FULL_KEYWORDS = [
    "全面分析", "深度分析", "详细分析", "完整分析",
    "帮我分析", "给我分析", "出一份",
    "研报", "研究报告", "投资建议",
    "能不能买", "该不该买", "要不要卖",
    "操作建议", "投资策略",
]

# 闲聊关键词（直接返回，不调用 LLM）
CHAT_KEYWORDS = [
    # 问候
    "你好", "您好", "hi", "hello", "嗨", "哈喽", "早上好", "下午好", "晚上好",
    # 感谢
    "谢谢", "感谢", "thanks", "多谢", "太感谢",
    # 告别
    "再见", "拜拜", "bye", "回见", "下次见",
    # 确认
    "好的", "好", "ok", "明白", "知道了", "收到",
    # 其他
    "在吗", "在不在", "你是谁", "你是什么",
]


class QueryRouter:
    """
    查询路由器

    根据查询内容判断应该使用哪种 Agent 处理。
    """

    def __init__(self):
        """初始化路由器"""
        self._compile_patterns()
        logger.info("QueryRouter 初始化完成")

    def _compile_patterns(self):
        """编译正则表达式模式"""
        # 闲聊模式（最高优先级）
        self._chat_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in CHAT_KEYWORDS),
            re.IGNORECASE
        )

        # 完整分析模式
        self._full_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in FULL_KEYWORDS),
            re.IGNORECASE
        )

        # 分析模式
        self._analysis_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in ANALYSIS_KEYWORDS),
            re.IGNORECASE
        )

        # 快速查询模式
        self._quick_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in QUICK_KEYWORDS),
            re.IGNORECASE
        )

    def route(self, query: str) -> QueryType:
        """
        路由查询到合适的 Agent

        优先级：chat > index_quick > full > analysis > quick

        Args:
            query: 用户查询

        Returns:
            QueryType: 查询类型
        """
        query = query.strip()

        # 0. 检查闲聊关键词（最高优先级，直接返回不调用 LLM）
        # 只有当查询很短且匹配闲聊关键词时才路由到 CHAT
        if len(query) <= 20 and self._chat_pattern.search(query):
            # 确保不包含股票相关内容
            if not self._quick_pattern.search(query) and not self._analysis_pattern.search(query):
                logger.debug(f"路由到 CHAT: {query[:50]}")
                return QueryType.CHAT

        # 0.5 简短的指数/大盘查询 -> QUICK（优化：避免简单查询走 ANALYSIS）
        # 但如果包含分析类关键词，则跳过快速路由
        if len(query) < 30:
            index_keywords = ["大盘", "指数", "上证", "深证", "创业板", "沪指", "深指", "今天行情", "今日行情"]
            analysis_exclude = ["分析", "走势", "趋势", "预测", "研判", "解读"]
            if any(kw in query for kw in index_keywords):
                # 如果同时包含分析关键词，不走快速路由
                if not any(kw in query for kw in analysis_exclude):
                    logger.debug(f"路由到 QUICK (指数快速查询): {query[:50]}")
                    return QueryType.QUICK

        # 1. 检查完整分析关键词
        if self._full_pattern.search(query):
            logger.debug(f"路由到 FULL: {query[:50]}")
            return QueryType.FULL

        # 2. 检查分析类关键词
        if self._analysis_pattern.search(query):
            logger.debug(f"路由到 ANALYSIS: {query[:50]}")
            return QueryType.ANALYSIS

        # 3. 检查快速查询关键词
        if self._quick_pattern.search(query):
            logger.debug(f"路由到 QUICK: {query[:50]}")
            return QueryType.QUICK

        # 4. 默认使用快速模式（更快）
        logger.debug(f"默认路由到 QUICK: {query[:50]}")
        return QueryType.QUICK

    def get_route_reason(self, query: str) -> str:
        """
        获取路由原因（调试用）

        Args:
            query: 用户查询

        Returns:
            str: 路由原因说明
        """
        query = query.strip()

        # 查找匹配的关键词
        if len(query) <= 20:
            chat_match = self._chat_pattern.search(query)
            if chat_match and not self._quick_pattern.search(query) and not self._analysis_pattern.search(query):
                return f"匹配闲聊关键词: '{chat_match.group()}'"

        full_match = self._full_pattern.search(query)
        if full_match:
            return f"匹配完整分析关键词: '{full_match.group()}'"

        analysis_match = self._analysis_pattern.search(query)
        if analysis_match:
            return f"匹配分析关键词: '{analysis_match.group()}'"

        quick_match = self._quick_pattern.search(query)
        if quick_match:
            return f"匹配快速查询关键词: '{quick_match.group()}'"

        return "无匹配关键词，默认使用快速模式"


# 单例
_router_instance: Optional[QueryRouter] = None


def get_router() -> QueryRouter:
    """获取 QueryRouter 单例"""
    global _router_instance
    if _router_instance is None:
        _router_instance = QueryRouter()
    return _router_instance
