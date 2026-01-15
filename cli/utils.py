import questionary
from typing import List, Optional, Tuple, Dict

from cli.models import AnalystType

ANALYST_ORDER = [
    ("Market Analyst", AnalystType.MARKET),
    ("Social Media Analyst", AnalystType.SOCIAL),
    ("News Analyst", AnalystType.NEWS),
    ("Fundamentals Analyst", AnalystType.FUNDAMENTALS),
]


def select_market():
    """Select stock market"""
    markets = {
        "1": {
            "name": "US Stock",
            "default": "SPY",
            "examples": ["SPY", "AAPL", "TSLA", "NVDA", "MSFT"],
            "format": "Stock symbol (e.g., AAPL)",
            "pattern": r'^[A-Z]{1,5}$',
            "data_source": "yahoo_finance"
        },
        "2": {
            "name": "China A-Share",
            "default": "600036",
            "examples": ["000001", "600036", "000858", "300001", "688001"],
            "format": "6-digit code (e.g., 600036, 000001)",
            "pattern": r'^\d{6}$',
            "data_source": "tongdaxin"
        }
    }

    choices = []
    for key, market in markets.items():
        examples_str = ", ".join(market["examples"][:3])
        display = f"{market['name']} - Examples: {examples_str}"
        choices.append(questionary.Choice(display, value=key))

    choice = questionary.select(
        "Select Stock Market:",
        choices=choices,
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:cyan noinherit"),
                ("highlighted", "fg:cyan noinherit"),
                ("pointer", "fg:cyan noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        from rich.console import Console
        console = Console()
        console.print("\n[red]No market selected. Exiting...[/red]")
        exit(1)

    selected_market = markets[choice]
    from rich.console import Console
    console = Console()
    console.print(f"[green]✅ Selected: {selected_market['name']}[/green]")
    return selected_market


def get_ticker(market=None) -> str:
    """Prompt the user to enter a ticker symbol with market-specific validation."""
    if market is None:
        # Fallback to original behavior for backward compatibility
        ticker = questionary.text(
            "Enter the ticker symbol to analyze:",
            validate=lambda x: len(x.strip()) > 0 or "Please enter a valid ticker symbol.",
            style=questionary.Style(
                [
                    ("text", "fg:green"),
                    ("highlighted", "noinherit"),
                ]
            ),
        ).ask()

        if not ticker:
            from rich.console import Console
            console = Console()
            console.print("\n[red]No ticker symbol provided. Exiting...[/red]")
            exit(1)

        return ticker.strip().upper()

    # Market-specific ticker input with validation
    from rich.console import Console
    console = Console()

    console.print(f"\n[dim]Format requirement: {market['format']}[/dim]")
    console.print(f"[dim]Examples: {', '.join(market['examples'][:3])}[/dim]")

    while True:
        ticker = questionary.text(
            f"Enter {market['name']} ticker symbol:",
            default=market['default'],
            style=questionary.Style(
                [
                    ("text", "fg:green"),
                    ("highlighted", "noinherit"),
                ]
            ),
        ).ask()

        if not ticker:
            console.print("\n[red]No ticker symbol provided. Exiting...[/red]")
            exit(1)

        # Validate ticker format
        import re
        ticker_to_check = ticker.upper() if market['data_source'] != 'tongdaxin' else ticker

        if re.match(market['pattern'], ticker_to_check):
            # For A-shares, return pure numeric code
            if market['data_source'] == 'tongdaxin':
                console.print(f"[green]✅ Valid A-share code: {ticker} (will use TongDaXin data source)[/green]")
                return ticker
            else:
                console.print(f"[green]✅ Valid ticker: {ticker.upper()}[/green]")
                return ticker.upper()
        else:
            console.print(f"[red]❌ Invalid ticker format[/red]")
            console.print(f"[yellow]Please use correct format: {market['format']}[/yellow]")


def get_analysis_date() -> str:
    """Prompt the user to enter a date in YYYY-MM-DD format."""
    import re
    from datetime import datetime

    def validate_date(date_str: str) -> bool:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    date = questionary.text(
        "Enter the analysis date (YYYY-MM-DD):",
        validate=lambda x: validate_date(x.strip())
        or "Please enter a valid date in YYYY-MM-DD format.",
        style=questionary.Style(
            [
                ("text", "fg:green"),
                ("highlighted", "noinherit"),
            ]
        ),
    ).ask()

    if not date:
        console.print("\n[red]No date provided. Exiting...[/red]")
        exit(1)

    return date.strip()


def select_analysts() -> List[AnalystType]:
    """Select analysts using an interactive checkbox."""
    choices = questionary.checkbox(
        "Select Your [Analysts Team]:",
        choices=[
            questionary.Choice(display, value=value) for display, value in ANALYST_ORDER
        ],
        instruction="\n- Press Space to select/unselect analysts\n- Press 'a' to select/unselect all\n- Press Enter when done",
        validate=lambda x: len(x) > 0 or "You must select at least one analyst.",
        style=questionary.Style(
            [
                ("checkbox-selected", "fg:green"),
                ("selected", "fg:green noinherit"),
                ("highlighted", "noinherit"),
                ("pointer", "noinherit"),
            ]
        ),
    ).ask()

    if not choices:
        console.print("\n[red]No analysts selected. Exiting...[/red]")
        exit(1)

    return choices


def select_research_depth() -> int:
    """Select research depth using an interactive selection."""

    # Define research depth options with their corresponding values
    DEPTH_OPTIONS = [
        ("Shallow - Quick research, few debate and strategy discussion rounds", 1),
        ("Medium - Middle ground, moderate debate rounds and strategy discussion", 3),
        ("Deep - Comprehensive research, in depth debate and strategy discussion", 5),
    ]

    choice = questionary.select(
        "Select Your [Research Depth]:",
        choices=[
            questionary.Choice(display, value=value) for display, value in DEPTH_OPTIONS
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:yellow noinherit"),
                ("highlighted", "fg:yellow noinherit"),
                ("pointer", "fg:yellow noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]No research depth selected. Exiting...[/red]")
        exit(1)

    return choice


def select_thinking_agent(provider) -> str:
    """Select LLM engine using an interactive selection."""

    # Define LLM engine options with their corresponding model names
    AGENT_OPTIONS = {
        "dashscope (alibaba cloud)": [
            ("Qwen-Turbo - 快速响应", "qwen-turbo"),
            ("Qwen-Plus - 性价比均衡 (推荐)", "qwen-plus"),
            ("Qwen-Max - 最强性能", "qwen-max"),
            ("Qwen-Max-LongContext - 超长上下文", "qwen-max-longcontext"),
        ],
        "openai": [
            ("GPT-5.2 - 最佳通用模型 (推荐)", "gpt-5.2"),
            ("GPT-5.2 Pro - 更难问题，深度思考", "gpt-5.2-pro"),
            ("GPT-5 mini - ⚠️上下文较小，可能溢出", "gpt-5-mini"),
            ("GPT-5 nano - ⚠️上下文较小，简单任务", "gpt-5-nano"),
        ],
        "anthropic": [
            ("Claude 3.5 Haiku - 快速推理", "claude-3-5-haiku-latest"),
            ("Claude 3.5 Sonnet - 高能力标准模型", "claude-3-5-sonnet-latest"),
            ("Claude 3.5 Opus - 最强大模型", "claude-3-opus-latest"),
        ],
        "google": [
            ("Gemini 2.0 Flash - 快速高效", "gemini-2.0-flash"),
            ("Gemini 1.5 Pro - 专业级模型", "gemini-1.5-pro"),
            ("Gemini 1.5 Flash - 平衡性能", "gemini-1.5-flash"),
        ],
        "openrouter": [
            ("Llama 4 Scout - Meta最新", "meta-llama/llama-4-scout"),
            ("DeepSeek V3 - 高性价比", "deepseek/deepseek-chat-v3-0324:free"),
            ("Gemini 2.0 Flash", "google/gemini-2.0-flash-exp:free"),
        ],
        "ollama": [
            ("Llama 3.1 本地", "llama3.1"),
            ("Llama 3.2 本地", "llama3.2"),
            ("Qwen3 本地", "qwen3"),
        ],
    }

    choice = questionary.select(
        "选择LLM模型:",
        choices=[
            questionary.Choice(display, value=value)
            for display, value in AGENT_OPTIONS[provider.lower()]
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]No LLM model selected. Exiting...[/red]")
        exit(1)

    return choice

def select_llm_provider() -> tuple[str, str]:
    """Select the LLM provider using interactive selection."""
    # Define LLM provider options with their corresponding endpoints
    # DashScope (Alibaba Cloud) is recommended for Chinese users
    BASE_URLS = [
        ("DashScope (Alibaba Cloud)", "https://dashscope.aliyuncs.com/api/v1"),
        ("OpenAI", "https://api.openai.com/v1"),
        ("Anthropic", "https://api.anthropic.com/"),
        ("Google", "https://generativelanguage.googleapis.com/v1"),
        ("Openrouter", "https://openrouter.ai/api/v1"),
        ("Ollama", "http://localhost:11434/v1"),
    ]
    
    choice = questionary.select(
        "Select your LLM Provider:",
        choices=[
            questionary.Choice(display, value=(display, value))
            for display, value in BASE_URLS
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]
        ),
    ).ask()
    
    if choice is None:
        console.print("\n[red]no OpenAI backend selected. Exiting...[/red]")
        exit(1)

    display_name, url = choice
    print(f"You selected: {display_name}\tURL: {url}")

    return display_name, url


def select_analysis_mode() -> str:
    """选择分析模式：单只股票或Portfolio批量分析"""
    from rich.console import Console
    console = Console()

    MODE_OPTIONS = [
        ("单只股票分析 - 深入分析一只股票", "single"),
        ("Portfolio批量分析 - 并行分析自选股组合", "portfolio"),
    ]

    choice = questionary.select(
        "选择分析模式:",
        choices=[
            questionary.Choice(display, value=value) for display, value in MODE_OPTIONS
        ],
        instruction="\n- 使用方向键选择\n- 按 Enter 确认",
        style=questionary.Style(
            [
                ("selected", "fg:cyan noinherit"),
                ("highlighted", "fg:cyan noinherit"),
                ("pointer", "fg:cyan noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]未选择分析模式，退出...[/red]")
        exit(1)

    return choice


def select_portfolio(portfolio_manager) -> Optional[str]:
    """选择要分析的Portfolio"""
    from rich.console import Console
    console = Console()

    portfolios = portfolio_manager.list_portfolios()

    if not portfolios:
        console.print("[yellow]暂无Portfolio，请先创建[/yellow]")
        console.print("[dim]使用命令: python -c \"from cli.main import app; app(['portfolio', 'create', '我的组合'])\"[/dim]")
        return None

    # 构建选项列表
    choices = []
    for p in portfolios:
        default_mark = " ✓" if p["is_default"] else ""
        display = f"{p['name']} ({p['stock_count']}只股票){default_mark}"
        choices.append(questionary.Choice(display, value=p["name"]))

    choice = questionary.select(
        "选择Portfolio:",
        choices=choices,
        instruction="\n- 使用方向键选择\n- 按 Enter 确认",
        style=questionary.Style(
            [
                ("selected", "fg:green noinherit"),
                ("highlighted", "fg:green noinherit"),
                ("pointer", "fg:green noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]未选择Portfolio，退出...[/red]")
        exit(1)

    return choice


def select_parallel_workers() -> int:
    """选择并行分析数量"""
    from rich.console import Console
    console = Console()

    WORKER_OPTIONS = [
        ("1 - 串行（最慢，省API）", 1),
        ("2 - 低并发", 2),
        ("3 - 标准（推荐）", 3),
        ("5 - 高并发", 5),
    ]

    choice = questionary.select(
        "并行分析数量:",
        choices=[
            questionary.Choice(display, value=value) for display, value in WORKER_OPTIONS
        ],
        instruction="\n- 并行数越高分析越快，但可能触发API限流",
        style=questionary.Style(
            [
                ("selected", "fg:yellow noinherit"),
                ("highlighted", "fg:yellow noinherit"),
                ("pointer", "fg:yellow noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        return 3  # 默认值

    return choice
