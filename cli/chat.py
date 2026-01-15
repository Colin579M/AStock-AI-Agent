"""
Chatbot CLI 入口

提供交互式聊天命令行界面。
"""
import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live

console = Console()

chat_app = typer.Typer(
    name="chat",
    help="交互式股票分析聊天助手"
)


def get_chatbot():
    """延迟导入并创建 Chatbot"""
    from tradingagents.chatbot import SimpleChatbot
    return SimpleChatbot()


@chat_app.callback(invoke_without_command=True)
def chat_main(
    ctx: typer.Context,
    single: bool = typer.Option(False, "--single", "-s", help="单次问答模式（不进入交互循环）"),
    question: Optional[str] = typer.Option(None, "--question", "-q", help="直接提问（配合 --single 使用）"),
):
    """
    启动交互式聊天

    示例：
        python -m cli chat                    # 进入交互模式
        python -m cli chat -s -q "茅台现在什么价？"  # 单次问答
    """
    if ctx.invoked_subcommand is not None:
        return

    # 欢迎消息
    console.print(Panel(
        "[bold cyan]股票分析助手[/bold cyan]\n\n"
        "我可以帮你查询股票数据和分析市场。\n"
        "支持的功能：\n"
        "  - 查询股票基本信息\n"
        "  - 查询估值指标（PE、PB等）\n"
        "  - 查询资金流向\n"
        "  - 查询新闻要点\n"
        "  - 查询基本面数据\n\n"
        "输入 [bold]exit[/bold] 或 [bold]quit[/bold] 退出\n"
        "输入 [bold]clear[/bold] 清空对话历史",
        title="欢迎",
        border_style="cyan"
    ))

    # 初始化 Chatbot
    with console.status("[bold green]正在初始化..."):
        try:
            chatbot = get_chatbot()
            console.print("[green]✓ 初始化完成[/green]\n")
        except Exception as e:
            console.print(f"[red]✗ 初始化失败: {e}[/red]")
            raise typer.Exit(1)

    # 单次问答模式
    if single:
        if question:
            _process_question(chatbot, question)
        else:
            # 从 stdin 读取
            import sys
            if not sys.stdin.isatty():
                question = sys.stdin.read().strip()
                if question:
                    _process_question(chatbot, question)
        return

    # 交互模式
    while True:
        try:
            user_input = console.input("[bold blue]You:[/bold blue] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]再见！[/yellow]")
                break

            if user_input.lower() == "clear":
                chatbot.clear_history()
                console.print("[green]对话历史已清空[/green]\n")
                continue

            if user_input.lower() == "history":
                _show_history(chatbot)
                continue

            _process_question(chatbot, user_input)

        except KeyboardInterrupt:
            console.print("\n[yellow]再见！[/yellow]")
            break
        except EOFError:
            break


def _process_question(chatbot, question: str):
    """处理用户问题"""
    with console.status("[bold green]思考中..."):
        try:
            response = chatbot.chat(question)
        except Exception as e:
            console.print(f"[red]处理失败: {e}[/red]\n")
            return

    # 显示回答
    console.print(f"\n[bold green]Assistant:[/bold green]")
    console.print(Panel(
        Markdown(response),
        border_style="green",
        padding=(1, 2)
    ))
    console.print()


def _show_history(chatbot):
    """显示对话历史"""
    history = chatbot.get_history()
    if not history:
        console.print("[dim]暂无对话历史[/dim]\n")
        return

    console.print("\n[bold]对话历史:[/bold]")
    for i, msg in enumerate(history, 1):
        role = "You" if msg["role"] == "user" else "Assistant"
        color = "blue" if msg["role"] == "user" else "green"
        content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        console.print(f"[{color}]{i}. {role}:[/{color}] {content}")
    console.print()


@chat_app.command("test")
def test_chatbot():
    """测试 Chatbot 是否正常工作"""
    console.print("[bold]测试 Chatbot...[/bold]\n")

    # 测试导入
    try:
        from tradingagents.chatbot import SimpleChatbot
        console.print("[green]✓ 模块导入成功[/green]")
    except Exception as e:
        console.print(f"[red]✗ 模块导入失败: {e}[/red]")
        return

    # 测试工具加载
    try:
        from tradingagents.chatbot.tools.registry import load_core_tools
        tools = load_core_tools()
        console.print(f"[green]✓ 加载 {len(tools)} 个工具: {[t.name for t in tools]}[/green]")
    except Exception as e:
        console.print(f"[red]✗ 工具加载失败: {e}[/red]")
        return

    # 测试初始化
    try:
        chatbot = SimpleChatbot()
        console.print("[green]✓ Chatbot 初始化成功[/green]")
    except Exception as e:
        console.print(f"[red]✗ Chatbot 初始化失败: {e}[/red]")
        return

    console.print("\n[bold green]所有测试通过！[/bold green]")


if __name__ == "__main__":
    chat_app()
