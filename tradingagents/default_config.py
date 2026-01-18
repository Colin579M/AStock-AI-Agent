import os

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
