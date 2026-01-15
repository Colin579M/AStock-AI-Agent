"""
Chatbot 配置
"""
from typing import Optional
from tradingagents.default_config import DEFAULT_CONFIG


CHATBOT_CONFIG = {
    # LLM 配置 (DeepSeek)
    "default_model": "deepseek-chat",    # 默认使用小模型
    "analysis_model": "deepseek-chat",   # 分析用大模型
    "max_tokens": 2000,

    # Agent 配置
    "max_iterations": 10,             # Agent 最大迭代次数
    "verbose": True,

    # 上下文配置
    "max_history_messages": 20,       # 保留的历史消息数

    # 工具配置
    "tool_timeout": 30,               # 工具调用超时（秒）
}


def get_chatbot_config(overrides: Optional[dict] = None) -> dict:
    """获取 Chatbot 配置，可选覆盖默认值"""
    config = {**DEFAULT_CONFIG, **CHATBOT_CONFIG}
    if overrides:
        config.update(overrides)
    return config
