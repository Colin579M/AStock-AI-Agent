"""
Chatbot 上下文管理模块

提供实体解析、对话状态管理等功能。
"""
from .entity_resolver import EntityResolver
from .state import ConversationState

__all__ = ["EntityResolver", "ConversationState"]
