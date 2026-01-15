"""
统一 Agent

单一 Agent 处理所有查询，简化架构，依赖 LLM 智能决策。
"""
import logging
from typing import Optional
from datetime import datetime

from .base_agent import BaseAgent, TOOL_DISPLAY_NAMES
from ..tools.registry import load_unified_tools
from ..config import get_chatbot_config
from tradingagents.graph.llm_factory import create_llm

logger = logging.getLogger(__name__)


UNIFIED_SYSTEM_PROMPT = """你是A股投资助手，可查询数据并提供分析。

## 工具使用
- 简单问题（价格、涨跌）→ 1个工具
- 分析问题 → 2-3个工具
- 不要反复调用同一工具

## 指数代码
大盘/上证→000001.SH | 深证→399001.SZ | 创业板→399006.SZ | 沪深300→000300.SH

## 板块查询
使用 get_sector_ranking 工具：
- indicator: 行业/概念/地域
- 问"什么板块有潜力"→用行业板块

## 排行榜
使用 get_stock_ranking 工具，**必须原样展示完整数据列表**，不省略任何股票。

## 分析框架
股票分析时：业务理解 → 财务健康度 → 估值水平 → 主要风险 → 投资观点

## 回答风格
- 数据驱动，关键数字**加粗**
- 给出明确观点
- 今天是 {today}

用中文简洁回答。"""


class UnifiedAgent(BaseAgent):
    """
    统一 Agent

    单一 Agent 处理所有类型的查询，通过优化的 system prompt
    让 LLM 自己决定调用哪些工具。
    """

    def _load_tools(self):
        """加载统一工具集（16个核心工具）"""
        return load_unified_tools()

    def _create_llm(self):
        """创建 LLM（使用 deepseek-chat）"""
        return create_llm(self.config)

    def _get_system_prompt(self) -> str:
        """获取统一系统提示"""
        return UNIFIED_SYSTEM_PROMPT

    @property
    def recursion_limit(self) -> int:
        """
        迭代限制

        平衡速度和能力：
        - 简单查询通常 1-2 次迭代
        - 复杂分析最多 10 次迭代
        """
        return 10

    @property
    def error_message(self) -> str:
        """错误提示"""
        return "抱歉，无法完成您的请求。请尝试更具体的问题。"


def create_unified_agent(config: Optional[dict] = None) -> UnifiedAgent:
    """
    创建 UnifiedAgent 实例

    Args:
        config: 可选配置

    Returns:
        UnifiedAgent: Agent 实例
    """
    return UnifiedAgent(config)


__all__ = ["UnifiedAgent", "create_unified_agent", "TOOL_DISPLAY_NAMES"]
