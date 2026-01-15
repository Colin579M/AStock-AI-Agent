"""
Memory 管理工具

管理TradingAgents的决策记忆：查看统计、手动追踪结果、清理旧记录
"""

import typer
from pathlib import Path
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tradingagents.default_config import DEFAULT_CONFIG

console = Console()


def get_memory_instance():
    """获取 Memory 实例"""
    from tradingagents.agents.utils.memory import FinancialSituationMemory

    return FinancialSituationMemory(
        name="trader_memory",
        config=DEFAULT_CONFIG
    )


memory_app = typer.Typer(
    name="memory",
    help="Memory 决策记忆管理工具"
)


@memory_app.command("stats")
def memory_stats(
    ticker: Optional[str] = typer.Option(None, "--ticker", "-t", help="按股票代码过滤")
):
    """显示 Memory 统计信息"""
    try:
        memory = get_memory_instance()
        stats = memory.get_performance_stats(ticker=ticker)

        # 创建统计面板
        title = f"Memory 统计" + (f" ({ticker})" if ticker else " (全部)")

        stats_text = f"""
[bold]总决策数[/bold]: {stats.get('total_decisions', 0)}
[bold]已追踪结果[/bold]: {stats.get('decisions_with_outcome', 0)}
[bold]待追踪[/bold]: {stats.get('total_decisions', 0) - stats.get('decisions_with_outcome', 0)}

[bold green]盈利次数[/bold green]: {stats.get('profit_count', 0)}
[bold red]亏损次数[/bold red]: {stats.get('loss_count', 0)}
[bold yellow]持平次数[/bold yellow]: {stats.get('breakeven_count', 0)}

[bold]胜率[/bold]: {stats.get('win_rate', 0):.1f}%
[bold]平均收益[/bold]: {stats.get('avg_return', 0):.2f}%
[bold]最佳收益[/bold]: {stats.get('best_return', 'N/A') if stats.get('best_return') is not None else 'N/A'}%
[bold]最差收益[/bold]: {stats.get('worst_return', 'N/A') if stats.get('worst_return') is not None else 'N/A'}%
[bold]平均持仓天数[/bold]: {stats.get('avg_days_held', 0):.1f}
"""
        console.print(Panel(stats_text, title=title, border_style="blue"))

    except Exception as e:
        console.print(f"[red]获取统计信息失败: {e}[/red]")


@memory_app.command("list")
def memory_list(
    limit: int = typer.Option(20, "--limit", "-n", help="显示记录数量"),
    ticker: Optional[str] = typer.Option(None, "--ticker", "-t", help="按股票代码过滤")
):
    """列出所有决策记录"""
    try:
        memory = get_memory_instance()
        all_records = memory.situation_collection.get(include=["metadatas"])

        if not all_records["ids"]:
            console.print("[yellow]暂无决策记录[/yellow]")
            return

        # 创建表格
        table = Table(title="决策记录列表")
        table.add_column("ID", style="dim", width=20)
        table.add_column("股票", style="cyan", width=8)
        table.add_column("日期", width=12)
        table.add_column("决策", justify="center", width=10)
        table.add_column("置信度", justify="right", width=8)
        table.add_column("结果已追踪", justify="center", width=10)
        table.add_column("收益率", justify="right", width=10)
        table.add_column("持仓天数", justify="right", width=10)

        count = 0
        for i, metadata in enumerate(all_records["metadatas"]):
            record_ticker = metadata.get("ticker", "")

            # 过滤
            if ticker and record_ticker != ticker:
                continue

            record_id = all_records["ids"][i]
            decision_date = metadata.get("decision_date", "未知")
            decision_type = metadata.get("decision_type", "未知")
            confidence = metadata.get("confidence", 0)
            outcome_updated = metadata.get("outcome_updated", False)
            actual_return = metadata.get("actual_return", 0)
            days_held = metadata.get("days_held", 0)

            # 结果颜色
            if outcome_updated:
                outcome_str = "[green]✓[/green]"
                if actual_return > 0:
                    return_str = f"[green]+{actual_return:.2f}%[/green]"
                elif actual_return < 0:
                    return_str = f"[red]{actual_return:.2f}%[/red]"
                else:
                    return_str = f"{actual_return:.2f}%"
            else:
                outcome_str = "[dim]✗[/dim]"
                return_str = "[dim]-[/dim]"

            table.add_row(
                record_id[:20] + "..." if len(record_id) > 20 else record_id,
                record_ticker,
                decision_date,
                decision_type,
                f"{confidence:.0%}",
                outcome_str,
                return_str,
                str(days_held) if outcome_updated else "[dim]-[/dim]"
            )

            count += 1
            if count >= limit:
                break

        console.print(table)
        console.print(f"\n[dim]显示 {count}/{len(all_records['ids'])} 条记录[/dim]")

    except Exception as e:
        console.print(f"[red]获取记录失败: {e}[/red]")


@memory_app.command("update-outcomes")
def memory_update_outcomes(
    ticker: Optional[str] = typer.Option(None, "--ticker", "-t", help="指定股票代码"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="当前日期 (YYYY-MM-DD)")
):
    """手动触发结果追踪更新"""
    from tradingagents.agents.utils.memory import get_historical_price

    try:
        memory = get_memory_instance()
        all_records = memory.situation_collection.get(include=["metadatas"])

        if not all_records["ids"]:
            console.print("[yellow]暂无决策记录[/yellow]")
            return

        current_date = date or datetime.now().strftime("%Y-%m-%d")
        console.print(f"[bold]开始追踪结果更新 (参考日期: {current_date})[/bold]\n")

        updated = 0
        skipped = 0
        errors = 0

        for i, metadata in enumerate(all_records["metadatas"]):
            record_id = all_records["ids"][i]
            record_ticker = metadata.get("ticker", "")
            outcome_updated = metadata.get("outcome_updated", False)
            decision_date = metadata.get("decision_date", "")

            # 过滤
            if ticker and record_ticker != ticker:
                continue
            if outcome_updated:
                skipped += 1
                continue
            if decision_date == current_date or not decision_date:
                skipped += 1
                continue

            try:
                # 获取决策日价格
                decision_price = get_historical_price(record_ticker, decision_date)
                if decision_price is None:
                    console.print(f"[yellow]  跳过 {record_id}: 无法获取 {decision_date} 的价格[/yellow]")
                    errors += 1
                    continue

                # 获取当前价格
                current_price = get_historical_price(record_ticker, current_date)
                if current_price is None:
                    console.print(f"[yellow]  跳过 {record_id}: 无法获取 {current_date} 的价格[/yellow]")
                    errors += 1
                    continue

                # 计算收益
                actual_return = (current_price - decision_price) / decision_price * 100
                decision_type = metadata.get("decision_type", "HOLD")
                if decision_type in ["SELL", "STRONG_SELL", "REDUCE"]:
                    actual_return = -actual_return

                # 计算天数
                d1 = datetime.strptime(decision_date, "%Y-%m-%d")
                d2 = datetime.strptime(current_date, "%Y-%m-%d")
                days_held = (d2 - d1).days

                # 更新
                success = memory.update_outcome(
                    record_id=record_id,
                    actual_return=actual_return,
                    days_held=days_held,
                    exit_date=current_date,
                    exit_reason="手动追踪更新"
                )

                if success:
                    updated += 1
                    color = "green" if actual_return > 0 else "red"
                    console.print(
                        f"  [green]✓[/green] {record_ticker} ({decision_date}): "
                        f"[{color}]{actual_return:+.2f}%[/{color}] "
                        f"({decision_price:.2f} → {current_price:.2f}, {days_held}天)"
                    )
                else:
                    errors += 1

            except Exception as e:
                console.print(f"[red]  ✗ {record_id}: {e}[/red]")
                errors += 1

        console.print(f"\n[bold]追踪完成[/bold]: 更新 {updated} 条, 跳过 {skipped} 条, 错误 {errors} 条")

    except Exception as e:
        console.print(f"[red]追踪更新失败: {e}[/red]")


@memory_app.command("health")
def memory_health():
    """检查 Memory 系统健康状态"""
    try:
        memory = get_memory_instance()
        health = memory.health_check()

        # 状态颜色
        status_colors = {
            "healthy": "green",
            "degraded": "yellow",
            "unhealthy": "red"
        }
        status_color = status_colors.get(health["status"], "white")

        console.print(f"\n[bold]Memory 系统状态: [{status_color}]{health['status'].upper()}[/{status_color}][/bold]\n")

        # 检查项
        table = Table(title="检查项")
        table.add_column("项目", style="cyan")
        table.add_column("状态", justify="center")
        table.add_column("详情")

        for check_name, check_result in health["checks"].items():
            status = check_result.get("status", "unknown")
            status_icon = "✓" if status == "ok" else ("⚠" if status == "warning" else "✗")
            status_style = "green" if status == "ok" else ("yellow" if status == "warning" else "red")

            details = []
            for k, v in check_result.items():
                if k != "status":
                    details.append(f"{k}: {v}")

            table.add_row(
                check_name,
                f"[{status_style}]{status_icon}[/{status_style}]",
                ", ".join(details) if details else "-"
            )

        console.print(table)

        # 警告
        if health["warnings"]:
            console.print("\n[yellow]警告:[/yellow]")
            for w in health["warnings"]:
                console.print(f"  ⚠ {w}")

        # 错误
        if health["errors"]:
            console.print("\n[red]错误:[/red]")
            for e in health["errors"]:
                console.print(f"  ✗ {e}")

    except Exception as e:
        console.print(f"[red]健康检查失败: {e}[/red]")


@memory_app.command("cleanup")
def memory_cleanup(
    days: int = typer.Option(365, "--days", "-d", help="保留的最大天数"),
    keep_min: int = typer.Option(100, "--keep-min", "-k", help="至少保留的记录数"),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="模拟运行/实际执行")
):
    """清理过期的历史记录"""
    try:
        memory = get_memory_instance()

        if dry_run:
            console.print("[yellow]模拟运行模式 (使用 --execute 实际执行)[/yellow]\n")

        # 获取当前记录数
        all_records = memory.situation_collection.get(include=["metadatas"])
        total_before = len(all_records["ids"])

        console.print(f"当前记录数: {total_before}")
        console.print(f"保留策略: {days}天以内 或 至少保留 {keep_min} 条\n")

        if dry_run:
            # 模拟计算将删除多少
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            to_delete = 0

            for metadata in all_records["metadatas"]:
                created_at = metadata.get("created_at")
                if created_at:
                    try:
                        record_date = datetime.fromisoformat(created_at)
                        if record_date < cutoff_date:
                            to_delete += 1
                    except (ValueError, TypeError):
                        pass

            max_deletable = max(0, total_before - keep_min)
            actual_delete = min(to_delete, max_deletable)

            console.print(f"[yellow]将删除 {actual_delete} 条记录 (共找到 {to_delete} 条过期)[/yellow]")
            console.print(f"[yellow]删除后剩余 {total_before - actual_delete} 条[/yellow]")
        else:
            result = memory.cleanup_old_records(max_age_days=days, keep_min_records=keep_min)
            console.print(f"[green]清理完成[/green]")
            console.print(f"  删除前: {result['total_before']} 条")
            console.print(f"  已删除: {result['deleted']} 条")
            console.print(f"  删除后: {result['total_after']} 条")

    except Exception as e:
        console.print(f"[red]清理失败: {e}[/red]")
