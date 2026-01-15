"""
TradingAgents Chatbot 模块

提供交互式对话功能，支持自动调用数据工具回答股票相关问题。

Phase 1: SimpleChatbot - 基础 ReAct Agent
Phase 2: EnhancedChatbot - 实体解析 + 上下文记忆
Phase 3: ChatbotGraph - 路由 + 多 Agent 协作
"""
from .simple_chat import SimpleChatbot, create_chatbot
from .enhanced_chat import EnhancedChatbot, create_enhanced_chatbot
from .graph import ChatbotGraph, create_chatbot_graph
from .config import get_chatbot_config, CHATBOT_CONFIG

__all__ = [
    # Phase 1
    "SimpleChatbot",
    "create_chatbot",
    # Phase 2
    "EnhancedChatbot",
    "create_enhanced_chatbot",
    # Phase 3
    "ChatbotGraph",
    "create_chatbot_graph",
    # Config
    "get_chatbot_config",
    "CHATBOT_CONFIG",
]
