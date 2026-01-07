# LLM Adapters for TradingAgents

__all__ = []

# DashScope adapter (optional)
try:
    from .dashscope_adapter import ChatDashScope
    __all__.append("ChatDashScope")
except ImportError:
    ChatDashScope = None

# OpenAI Responses API adapter (optional)
try:
    from .openai_responses_adapter import ChatOpenAIResponses
    __all__.append("ChatOpenAIResponses")
except ImportError:
    ChatOpenAIResponses = None
