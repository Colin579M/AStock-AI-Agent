"""
Portfolio并行分析模块

支持并行分析portfolio中的所有股票，生成汇总报告
"""

import re
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout

console = Console()


class PortfolioAnalyzer:
    """Portfolio并行分析器"""

    def __init__(self, config: dict, max_workers: int = 3):
        """
        初始化分析器

        Args:
            config: 分析配置
            max_workers: 最大并行数（默认3，避免API限流）
        """
        self.config = config
        self.max_workers = max_workers
        self.results = {}

    def analyze_single(
        self,
        ticker: str,
        analysis_date: str,
        analysts: List[str],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        分析单只股票

        Args:
            ticker: 股票代码
            analysis_date: 分析日期
            analysts: 分析师列表
            progress_callback: 进度回调函数

        Returns:
            分析结果字典
        """
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        result = {
            "ticker": ticker,
            "status": "pending",
            "decision": None,
            "target_price": None,
            "stop_loss": None,
            "confidence": None,
            "summary": None,
            "error": None,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
        }

        try:
            # 创建独立的Graph实例
            graph = TradingAgentsGraph(analysts, config=self.config, debug=False)

            # 创建初始状态
            init_state = graph.propagator.create_initial_state(ticker, analysis_date)

            # 运行分析
            final_state = None
            for chunk in graph.graph.stream(init_state, {"recursion_limit": self.config.get("max_recur_limit", 100)}):
                final_state = chunk
                if progress_callback:
                    progress_callback(ticker, "running")

            # 提取结果
            if final_state:
                result = self._extract_result(ticker, final_state, result)
                result["status"] = "completed"
            else:
                result["status"] = "no_result"
                result["error"] = "分析未产生结果"

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            console.print(f"[red]分析 {ticker} 失败: {e}[/red]")
            traceback.print_exc()

        result["end_time"] = datetime.now().isoformat()
        return result

    def _extract_result(self, ticker: str, state: Dict, result: Dict) -> Dict:
        """
        从分析状态中提取关键结果

        Args:
            ticker: 股票代码
            state: 最终状态
            result: 结果字典

        Returns:
            更新后的结果字典
        """
        # 优先从consolidation_report提取
        consolidation = state.get("consolidation_report", "")
        final_decision = state.get("final_trade_decision", "")

        # 合并文本用于搜索
        all_text = f"{consolidation}\n{final_decision}"

        # 提取决策类型
        result["decision"] = self._extract_decision(all_text)

        # 提取目标价
        target_match = re.search(r'目标价[位]?[：:]\s*([\d.]+)', all_text)
        if target_match:
            result["target_price"] = float(target_match.group(1))

        # 提取止损价
        stop_match = re.search(r'止损价[位]?[：:]\s*([\d.]+)', all_text)
        if stop_match:
            result["stop_loss"] = float(stop_match.group(1))

        # 提取置信度
        conf_match = re.search(r'置信度[：:]\s*([\d.]+)%?', all_text)
        if conf_match:
            conf_val = float(conf_match.group(1))
            result["confidence"] = conf_val if conf_val <= 1 else conf_val / 100

        # 提取简报（从执行摘要或核心逻辑）
        result["summary"] = self._extract_summary(all_text)

        return result

    def _extract_decision(self, text: str) -> str:
        """提取投资决策"""
        text_upper = text.upper()

        # 中文决策词检测（按优先级）
        if "强烈买入" in text:
            return "强烈买入"
        elif "强烈卖出" in text:
            return "强烈卖出"
        elif "【买入】" in text or "投资评级：买入" in text:
            return "买入"
        elif "【卖出】" in text or "投资评级：卖出" in text:
            return "卖出"
        elif "【减持】" in text or "投资评级：减持" in text:
            return "减持"
        elif "【持有】" in text or "投资评级：持有" in text:
            return "持有"
        # 英文决策词
        elif "STRONG BUY" in text_upper:
            return "强烈买入"
        elif "BUY" in text_upper and "SELL" not in text_upper:
            return "买入"
        elif "SELL" in text_upper:
            return "卖出"
        elif "HOLD" in text_upper:
            return "持有"

        return "未知"

    def _extract_summary(self, text: str) -> str:
        """提取简报摘要"""
        # 尝试从核心投资逻辑提取
        logic_match = re.search(r'核心投资逻辑[（(]?[^）)]*[）)]?\s*\n([\s\S]*?)(?=\n##|\n主要风险|$)', text)
        if logic_match:
            lines = logic_match.group(1).strip().split('\n')
            # 取前两行作为简报
            summary_lines = [l.strip() for l in lines[:2] if l.strip()]
            if summary_lines:
                return "; ".join(summary_lines)[:100]

        # 尝试从执行摘要提取
        exec_match = re.search(r'执行摘要[\s\S]*?投资评级[：:][^\n]*\n([^\n]+)', text)
        if exec_match:
            return exec_match.group(1).strip()[:100]

        return "详见完整报告"

    def analyze_portfolio(
        self,
        portfolio_name: str,
        tickers: List[str],
        analysis_date: str,
        analysts: List[str] = None
    ) -> Dict[str, Any]:
        """
        并行分析整个portfolio

        Args:
            portfolio_name: portfolio名称
            tickers: 股票代码列表
            analysis_date: 分析日期
            analysts: 分析师列表（默认全部）

        Returns:
            分析结果汇总
        """
        if analysts is None:
            analysts = ["market", "social", "news", "fundamentals"]

        total = len(tickers)
        completed = 0
        results = {}

        console.print(f"\n[bold]开始分析 Portfolio: {portfolio_name}[/bold]")
        console.print(f"股票数量: {total} | 并行度: {self.max_workers} | 日期: {analysis_date}\n")

        start_time = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"分析进度", total=total)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                futures = {
                    executor.submit(
                        self.analyze_single,
                        ticker,
                        analysis_date,
                        analysts
                    ): ticker
                    for ticker in tickers
                }

                # 收集结果
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        result = future.result()
                        results[ticker] = result
                        status_icon = "✓" if result["status"] == "completed" else "✗"
                        decision = result.get("decision", "未知")
                        progress.console.print(f"  {status_icon} {ticker}: {decision}")
                    except Exception as e:
                        results[ticker] = {
                            "ticker": ticker,
                            "status": "failed",
                            "error": str(e),
                            "decision": "错误"
                        }
                        progress.console.print(f"  ✗ {ticker}: [red]失败 - {e}[/red]")

                    completed += 1
                    progress.update(task, completed=completed)

        elapsed = time.time() - start_time

        # 生成汇总
        summary = self._generate_summary(portfolio_name, analysis_date, results, elapsed)

        return {
            "portfolio_name": portfolio_name,
            "analysis_date": analysis_date,
            "results": results,
            "summary": summary,
            "elapsed_seconds": elapsed
        }

    def _generate_summary(
        self,
        portfolio_name: str,
        analysis_date: str,
        results: Dict[str, Dict],
        elapsed: float
    ) -> Dict:
        """生成分析汇总"""
        # 统计各类决策
        decision_counts = {}
        for ticker, result in results.items():
            decision = result.get("decision", "未知")
            decision_counts[decision] = decision_counts.get(decision, 0) + 1

        total = len(results)
        completed = sum(1 for r in results.values() if r.get("status") == "completed")
        failed = total - completed

        return {
            "total_stocks": total,
            "completed": completed,
            "failed": failed,
            "decision_distribution": decision_counts,
            "elapsed_seconds": elapsed
        }

    def display_results(self, analysis_result: Dict):
        """显示分析结果表格"""
        portfolio_name = analysis_result["portfolio_name"]
        analysis_date = analysis_result["analysis_date"]
        results = analysis_result["results"]
        summary = analysis_result["summary"]

        # 统计面板
        decision_dist = summary["decision_distribution"]
        stats_text = f"[bold]统计汇总[/bold]\n"
        for decision, count in sorted(decision_dist.items(), key=lambda x: -x[1]):
            pct = count / summary["total_stocks"] * 100
            color = self._get_decision_color(decision)
            stats_text += f"  [{color}]{decision}: {count}只 ({pct:.0f}%)[/{color}]\n"
        stats_text += f"\n完成: {summary['completed']} | 失败: {summary['failed']}"
        stats_text += f"\n耗时: {summary['elapsed_seconds']:.1f}秒"

        console.print(Panel(stats_text, title=f"Portfolio: {portfolio_name} ({analysis_date})"))

        # 详细表格
        table = Table(title="个股分析结果")
        table.add_column("股票", style="cyan", width=8)
        table.add_column("评级", justify="center", width=8)
        table.add_column("目标价", justify="right", width=8)
        table.add_column("止损价", justify="right", width=8)
        table.add_column("简报", width=40)

        # 按评级排序显示
        sorted_results = sorted(
            results.items(),
            key=lambda x: self._decision_priority(x[1].get("decision", "未知"))
        )

        for ticker, result in sorted_results:
            decision = result.get("decision", "未知")
            color = self._get_decision_color(decision)
            target = f"{result.get('target_price', '-')}" if result.get('target_price') else "-"
            stop = f"{result.get('stop_loss', '-')}" if result.get('stop_loss') else "-"
            summary_text = result.get("summary", "-") or "-"

            table.add_row(
                ticker,
                f"[{color}]{decision}[/{color}]",
                target,
                stop,
                summary_text[:40] + "..." if len(summary_text) > 40 else summary_text
            )

        console.print(table)

    def _get_decision_color(self, decision: str) -> str:
        """获取决策对应的颜色"""
        colors = {
            "强烈买入": "bold green",
            "买入": "green",
            "持有": "yellow",
            "减持": "orange3",
            "卖出": "red",
            "强烈卖出": "bold red",
            "未知": "dim",
            "错误": "red"
        }
        return colors.get(decision, "white")

    def _decision_priority(self, decision: str) -> int:
        """决策排序优先级（买入在前）"""
        priorities = {
            "强烈买入": 0,
            "买入": 1,
            "持有": 2,
            "减持": 3,
            "卖出": 4,
            "强烈卖出": 5,
            "未知": 6,
            "错误": 7
        }
        return priorities.get(decision, 99)

    def save_summary_report(
        self,
        analysis_result: Dict,
        output_dir: Path
    ) -> Path:
        """
        保存汇总报告到文件

        Args:
            analysis_result: 分析结果
            output_dir: 输出目录

        Returns:
            报告文件路径
        """
        portfolio_name = analysis_result["portfolio_name"]
        analysis_date = analysis_result["analysis_date"]
        results = analysis_result["results"]
        summary = analysis_result["summary"]

        # 创建输出目录
        report_dir = output_dir / "portfolios" / portfolio_name / analysis_date
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = report_dir / "summary.md"

        # 生成Markdown报告
        md_content = f"""# Portfolio分析报告: {portfolio_name}

**分析日期**: {analysis_date}
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**股票数量**: {summary['total_stocks']}
**分析耗时**: {summary['elapsed_seconds']:.1f}秒

---

## 统计汇总

| 评级 | 数量 | 占比 |
|------|------|------|
"""
        for decision, count in sorted(summary["decision_distribution"].items(), key=lambda x: -x[1]):
            pct = count / summary["total_stocks"] * 100
            md_content += f"| {decision} | {count} | {pct:.0f}% |\n"

        md_content += """
---

## 个股分析

| 股票 | 评级 | 目标价 | 止损价 | 简报 |
|------|------|--------|--------|------|
"""
        for ticker, result in sorted(results.items(), key=lambda x: self._decision_priority(x[1].get("decision", "未知"))):
            decision = result.get("decision", "未知")
            target = result.get("target_price", "-") or "-"
            stop = result.get("stop_loss", "-") or "-"
            summary_text = (result.get("summary", "-") or "-")[:50]
            md_content += f"| {ticker} | {decision} | {target} | {stop} | {summary_text} |\n"

        md_content += """
---

## 详细报告

各股票的完整分析报告请查看对应目录:
"""
        for ticker in results.keys():
            md_content += f"- `results/{ticker}/{analysis_date}/reports/`\n"

        md_content += """
---

*由 TradingAgents AI Research 系统生成*
"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        console.print(f"\n[green]汇总报告已保存: {report_path}[/green]")
        return report_path
