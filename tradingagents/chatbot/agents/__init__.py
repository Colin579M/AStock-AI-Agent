"""
Chatbot Agent 模块

提供不同类型的 Agent：
- BaseAgent: Agent 基类
- QueryRouter: 查询分类路由
- QuickAgent: 快速查询（小模型）
- AnalysisAgent: 深度分析（大模型）
"""
from .router import QueryRouter, QueryType
from .base_agent import BaseAgent, TOOL_DISPLAY_NAMES
from .quick_agent import QuickAgent
from .analysis_agent import AnalysisAgent

__all__ = [
    "BaseAgent",
    "TOOL_DISPLAY_NAMES",
    "QueryRouter",
    "QueryType",
    "QuickAgent",
    "AnalysisAgent",
]
