"""
LLM Factory Module

提供统一的LLM实例创建接口，支持多种提供商:
- OpenAI (Chat Completions / Responses API)
- Anthropic (Claude)
- Google (Gemini)
- DashScope (阿里云通义千问)
- Ollama (本地部署)
- OpenRouter (多模型路由)
"""

import os
import logging
import threading
from typing import Dict, Any, Tuple

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# 延迟导入适配器，避免强制依赖
_DASHSCOPE_ADAPTER = None
_OPENAI_RESPONSES_ADAPTER = None
_DEEPSEEK_REASONER_ADAPTER = None
_adapter_lock = threading.Lock()  # 线程安全锁


def _get_dashscope_adapter():
    """延迟加载 DashScope 适配器（线程安全）"""
    global _DASHSCOPE_ADAPTER
    with _adapter_lock:
        if _DASHSCOPE_ADAPTER is None:
            try:
                from tradingagents.llm_adapters.dashscope_adapter import ChatDashScope
                _DASHSCOPE_ADAPTER = ChatDashScope
            except ImportError:
                _DASHSCOPE_ADAPTER = False
                logger.warning("DashScope adapter not available. Install: pip install dashscope")
        return _DASHSCOPE_ADAPTER if _DASHSCOPE_ADAPTER else None


def _get_openai_responses_adapter():
    """延迟加载 OpenAI Responses API 适配器（线程安全）"""
    global _OPENAI_RESPONSES_ADAPTER
    with _adapter_lock:
        if _OPENAI_RESPONSES_ADAPTER is None:
            try:
                from tradingagents.llm_adapters.openai_responses_adapter import ChatOpenAIResponses
                _OPENAI_RESPONSES_ADAPTER = ChatOpenAIResponses
            except ImportError:
                _OPENAI_RESPONSES_ADAPTER = False
                logger.debug("OpenAI Responses adapter not available, will use Chat Completions API")
        return _OPENAI_RESPONSES_ADAPTER if _OPENAI_RESPONSES_ADAPTER else None


def _get_deepseek_reasoner_adapter():
    """延迟加载 DeepSeek Reasoner 适配器（线程安全）"""
    global _DEEPSEEK_REASONER_ADAPTER
    with _adapter_lock:
        if _DEEPSEEK_REASONER_ADAPTER is None:
            try:
                from tradingagents.llm_adapters.deepseek_reasoner_adapter import ChatDeepSeekReasoner
                _DEEPSEEK_REASONER_ADAPTER = ChatDeepSeekReasoner
            except ImportError:
                _DEEPSEEK_REASONER_ADAPTER = False
                logger.debug("DeepSeek Reasoner adapter not available, will use ChatOpenAI")
        return _DEEPSEEK_REASONER_ADAPTER if _DEEPSEEK_REASONER_ADAPTER else None


def create_llm(config: Dict[str, Any], llm_type: str = "deep"):
    """
    创建LLM实例

    Args:
        config: 配置字典，需包含:
            - llm_provider: 提供商名称 (openai/anthropic/google/dashscope/ollama/openrouter)
            - deep_think_llm: 深度思考模型名称
            - quick_think_llm: 快速思考模型名称
            - backend_url: API端点URL (可选)
        llm_type: "deep" 或 "quick"

    Returns:
        LangChain Chat Model 实例

    Raises:
        ValueError: 不支持的提供商或缺少必要依赖
    """
    provider = config.get("llm_provider", "openai").lower()
    model_name = config.get(f"{llm_type}_think_llm")
    backend_url = config.get("backend_url")

    logger.info(f"Creating {llm_type} LLM: provider={provider}, model={model_name}")

    # OpenAI 或兼容 API
    if provider == "openai":
        return _create_openai_llm(config, model_name, backend_url, llm_type)

    # Ollama / OpenRouter 使用 OpenAI 兼容接口
    if provider in ("ollama", "openrouter"):
        return ChatOpenAI(model=model_name, base_url=backend_url)

    # Anthropic (Claude)
    if provider == "anthropic":
        return ChatAnthropic(model=model_name, base_url=backend_url)

    # Google (Gemini)
    if provider == "google":
        return _create_google_llm(model_name)

    # DashScope (阿里云通义千问)
    if provider in ("dashscope", "alibaba") or "dashscope" in provider or "alibaba" in provider:
        return _create_dashscope_llm(model_name)

    raise ValueError(f"Unsupported LLM provider: {provider}. "
                    f"Supported: openai, anthropic, google, dashscope, ollama, openrouter")


def create_llm_pair(config: Dict[str, Any]) -> Tuple[Any, Any]:
    """
    创建深度思考和快速思考LLM对

    Args:
        config: 配置字典

    Returns:
        Tuple[deep_thinking_llm, quick_thinking_llm]
    """
    deep_llm = create_llm(config, "deep")
    quick_llm = create_llm(config, "quick")
    return deep_llm, quick_llm


def _create_openai_llm(config: Dict[str, Any], model_name: str, backend_url: str, llm_type: str):
    """创建 OpenAI LLM 实例"""
    # 检测是否是 DeepSeek
    is_deepseek = backend_url and "deepseek" in backend_url.lower()
    is_reasoner = model_name and "reasoner" in model_name.lower()

    # 从 config 获取 max_tokens，默认 2000（平衡速度和能力）
    max_tokens = config.get('max_tokens', 2000)

    if is_deepseek:
        # DeepSeek Reasoner 需要特殊适配器处理 reasoning_content
        if is_reasoner:
            ChatDeepSeekReasoner = _get_deepseek_reasoner_adapter()
            if ChatDeepSeekReasoner:
                # Reasoner 模式需要更多 tokens（thinking + output）
                reasoner_max_tokens = max(max_tokens, 8000)
                logger.info(f"检测到 DeepSeek Reasoner，使用专用适配器: {model_name}, max_tokens={reasoner_max_tokens}")
                return ChatDeepSeekReasoner(
                    model=model_name,
                    base_url=backend_url,
                    max_tokens=reasoner_max_tokens
                )
            else:
                logger.warning("DeepSeek Reasoner 适配器不可用，回退到 ChatOpenAI（可能不支持 tool calls）")

        # DeepSeek Chat 使用标准 ChatOpenAI
        logger.info(f"检测到 DeepSeek API，使用 Chat Completions API: {model_name}, max_tokens={max_tokens}")
        return ChatOpenAI(
            model=model_name,
            base_url=backend_url,
            temperature=0.1,
            max_tokens=max_tokens
        )

    # 尝试使用 Responses API (推荐用于 GPT-4.5/5 等新模型)
    ChatOpenAIResponses = _get_openai_responses_adapter()

    if ChatOpenAIResponses:
        reasoning_effort = "medium" if llm_type == "deep" else "low"
        return ChatOpenAIResponses(
            model=model_name,
            base_url=backend_url,
            reasoning_effort=reasoning_effort,
            max_tokens=4000
        )

    # 回退到 Chat Completions API
    return ChatOpenAI(model=model_name, base_url=backend_url)


def _create_google_llm(model_name: str):
    """创建 Google Gemini LLM 实例"""
    google_api_key = os.getenv('GOOGLE_API_KEY')
    if not google_api_key:
        logger.warning("GOOGLE_API_KEY not set in environment")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=google_api_key,
        temperature=0.1,
        max_tokens=2000
    )


def _create_dashscope_llm(model_name: str):
    """创建 DashScope (阿里云通义千问) LLM 实例"""
    ChatDashScope = _get_dashscope_adapter()

    if not ChatDashScope:
        raise ValueError(
            "DashScope adapter not available. "
            "Please install dashscope package: pip install dashscope"
        )

    return ChatDashScope(
        model=model_name,
        temperature=0.1,
        max_tokens=2000
    )


def get_supported_providers() -> list:
    """获取支持的LLM提供商列表"""
    providers = ["openai", "anthropic", "google", "ollama", "openrouter"]

    if _get_dashscope_adapter():
        providers.append("dashscope")

    return providers


def validate_llm_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证LLM配置

    Args:
        config: 配置字典

    Returns:
        Dict: {"valid": bool, "errors": list, "warnings": list}
    """
    errors = []
    warnings = []

    provider = config.get("llm_provider", "").lower()
    if not provider:
        errors.append("llm_provider is required")
    elif provider not in get_supported_providers() and provider not in ("dashscope", "alibaba"):
        errors.append(f"Unsupported provider: {provider}")

    if not config.get("deep_think_llm"):
        errors.append("deep_think_llm is required")

    if not config.get("quick_think_llm"):
        errors.append("quick_think_llm is required")

    # 检查特定提供商的配置
    if provider == "google" and not os.getenv('GOOGLE_API_KEY'):
        warnings.append("GOOGLE_API_KEY not set in environment")

    if provider in ("dashscope", "alibaba") and not os.getenv('DASHSCOPE_API_KEY'):
        warnings.append("DASHSCOPE_API_KEY not set in environment")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
