import os
import warnings
from typing import Dict, Any, List, Optional


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    验证配置有效性

    Args:
        config: 配置字典

    Returns:
        List[str]: 警告消息列表（空列表表示配置有效）

    Raises:
        ValueError: 配置存在严重错误时抛出
    """
    warnings_list = []
    errors = []

    # 1. 验证LLM提供商
    valid_providers = ["openai", "anthropic", "google", "dashscope", "ollama", "openrouter"]
    provider = config.get("llm_provider", "").lower()
    if provider not in valid_providers:
        errors.append(
            f"无效的llm_provider: '{provider}'。"
            f"支持的提供商: {', '.join(valid_providers)}"
        )

    # 2. 验证API密钥（根据提供商）
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            warnings_list.append(
                "未设置OPENAI_API_KEY环境变量，OpenAI调用将失败"
            )
    elif provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            warnings_list.append(
                "未设置ANTHROPIC_API_KEY环境变量，Anthropic调用将失败"
            )
    elif provider == "dashscope":
        if not os.getenv("DASHSCOPE_API_KEY"):
            warnings_list.append(
                "未设置DASHSCOPE_API_KEY环境变量，DashScope调用将失败"
            )

    # 3. 验证Tushare Token（中国市场必需）
    tushare_token = config.get("tushare_token") or os.getenv("TUSHARE_TOKEN")
    if not tushare_token:
        warnings_list.append(
            "未设置TUSHARE_TOKEN，中国A股数据获取将失败。"
            "获取Token: https://tushare.pro/register"
        )

    # 4. 验证数值参数范围
    max_debate = config.get("max_debate_rounds", 1)
    if not isinstance(max_debate, int) or max_debate < 1 or max_debate > 10:
        errors.append(
            f"max_debate_rounds必须为1-10之间的整数，当前值: {max_debate}"
        )

    max_risk = config.get("max_risk_discuss_rounds", 1)
    if not isinstance(max_risk, int) or max_risk < 1 or max_risk > 10:
        errors.append(
            f"max_risk_discuss_rounds必须为1-10之间的整数，当前值: {max_risk}"
        )

    # 5. 验证目录路径
    data_dir = config.get("data_dir")
    if data_dir:
        parent_dir = os.path.dirname(data_dir)
        if parent_dir and not os.path.exists(parent_dir):
            warnings_list.append(
                f"数据目录的父目录不存在: {parent_dir}，将自动创建"
            )

    # 如果有严重错误，抛出异常
    if errors:
        raise ValueError(
            "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return warnings_list


def get_validated_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    获取经过验证的配置

    Args:
        config: 自定义配置（可选），将与DEFAULT_CONFIG合并

    Returns:
        Dict[str, Any]: 验证后的配置字典
    """
    final_config = DEFAULT_CONFIG.copy()
    if config:
        final_config.update(config)

    # 验证配置
    warnings_list = validate_config(final_config)

    # 打印警告
    for warning in warnings_list:
        warnings.warn(f"配置警告: {warning}", UserWarning)

    return final_config


DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_dir": os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "data"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    # Supported providers: "openai", "anthropic", "google", "dashscope", "ollama", "openrouter"
    # For DashScope: set llm_provider="dashscope", deep_think_llm="qwen-plus", quick_think_llm="qwen-turbo"
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Tool settings
    "online_tools": True,

    # Tushare Pro API Token
    # 获取方式: https://tushare.pro/register
    # 设置环境变量 TUSHARE_TOKEN 或在此处直接配置
    "tushare_token": os.getenv("TUSHARE_TOKEN", ""),

    # ChromaDB 持久化存储路径（用于 Memory 模块）
    "chroma_db_path": os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "TradingAgents",
        "chroma_db"
    ),

    # Note: Database and cache configuration is now managed by .env file and config.database_manager
    # No database/cache settings in default config to avoid configuration conflicts
}
