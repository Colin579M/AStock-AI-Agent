"""
对话状态管理

跟踪对话上下文，包括当前讨论的股票、日期等。
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """
    对话状态

    跟踪多轮对话中的上下文信息。
    """

    # 当前讨论的股票
    current_ticker: Optional[str] = None

    # 当前分析日期
    current_date: Optional[str] = None

    # 对话中提到的所有股票
    mentioned_tickers: List[str] = field(default_factory=list)

    # 轮数统计
    turn_count: int = 0

    # 最近的工具调用结果缓存
    last_tool_results: Dict[str, Any] = field(default_factory=dict)

    # 用户偏好
    preferences: Dict[str, Any] = field(default_factory=dict)

    # 会话开始时间
    session_start: datetime = field(default_factory=datetime.now)

    def update_ticker(self, ticker: str):
        """
        更新当前讨论的股票

        Args:
            ticker: 股票代码
        """
        if ticker:
            self.current_ticker = ticker
            if ticker not in self.mentioned_tickers:
                self.mentioned_tickers.append(ticker)
            logger.debug(f"更新当前股票: {ticker}")

    def update_date(self, date: str):
        """
        更新当前分析日期

        Args:
            date: YYYYMMDD 格式日期
        """
        if date:
            self.current_date = date
            logger.debug(f"更新当前日期: {date}")

    def increment_turn(self):
        """增加对话轮数"""
        self.turn_count += 1

    def cache_tool_result(self, tool_name: str, result: Any):
        """
        缓存工具调用结果

        Args:
            tool_name: 工具名称
            result: 结果数据
        """
        self.last_tool_results[tool_name] = {
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "ticker": self.current_ticker,
            "date": self.current_date
        }

    def get_cached_result(self, tool_name: str) -> Optional[Any]:
        """
        获取缓存的工具结果

        Args:
            tool_name: 工具名称

        Returns:
            缓存的结果或 None
        """
        cached = self.last_tool_results.get(tool_name)
        if cached:
            return cached.get("result")
        return None

    def get_context_summary(self) -> str:
        """
        获取当前上下文摘要

        Returns:
            上下文摘要字符串
        """
        parts = []

        if self.current_ticker:
            parts.append(f"当前股票: {self.current_ticker}")

        if self.current_date:
            parts.append(f"分析日期: {self.current_date}")

        if self.mentioned_tickers:
            parts.append(f"提到的股票: {', '.join(self.mentioned_tickers)}")

        parts.append(f"对话轮数: {self.turn_count}")

        return " | ".join(parts) if parts else "无上下文"

    def reset(self):
        """重置状态"""
        self.current_ticker = None
        self.current_date = None
        self.mentioned_tickers = []
        self.turn_count = 0
        self.last_tool_results = {}
        self.session_start = datetime.now()
        logger.info("对话状态已重置")

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            状态字典
        """
        return {
            "current_ticker": self.current_ticker,
            "current_date": self.current_date,
            "mentioned_tickers": self.mentioned_tickers,
            "turn_count": self.turn_count,
            "session_start": self.session_start.isoformat(),
            "preferences": self.preferences
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        """
        从字典创建

        Args:
            data: 状态字典

        Returns:
            ConversationState 实例
        """
        state = cls()
        state.current_ticker = data.get("current_ticker")
        state.current_date = data.get("current_date")
        state.mentioned_tickers = data.get("mentioned_tickers", [])
        state.turn_count = data.get("turn_count", 0)
        state.preferences = data.get("preferences", {})

        session_start = data.get("session_start")
        if session_start:
            state.session_start = datetime.fromisoformat(session_start)

        return state


