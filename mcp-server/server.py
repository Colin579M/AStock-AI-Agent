#!/usr/bin/env python3
"""
A股智能分析 MCP Server

为 Claude Desktop 提供 A 股个股分析能力。

Tools:
- analyze_stock: 执行完整的个股分析
- resolve_ticker: 股票名称转代码
- check_env: 检查运行环境
- read_report: 读取已生成的分析报告
"""

import os
import sys
import json
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 导入股票名称解析
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude/skills/a-share-analyzer/scripts"))
try:
    from resolve_ticker import resolve_ticker, COMMON_STOCKS
except ImportError:
    COMMON_STOCKS = {}
    def resolve_ticker(name):
        return {"error": "resolve_ticker module not found"}

# 创建 MCP Server
server = Server("a-share-analyzer")


def get_ticker_suffix(ticker: str) -> str:
    """获取股票代码后缀"""
    if len(ticker) != 6 or not ticker.isdigit():
        return ticker
    prefix = ticker[:3]
    if prefix in ['600', '601', '603', '605', '688']:
        return f"{ticker}.SH"
    elif prefix in ['000', '002', '003', '300', '301']:
        return f"{ticker}.SZ"
    return ticker


def check_environment() -> dict:
    """检查运行环境"""
    issues = []
    info = {}

    # 检查 TUSHARE_TOKEN
    if not os.getenv("TUSHARE_TOKEN"):
        issues.append("未设置 TUSHARE_TOKEN 环境变量")
    else:
        info["tushare"] = "已配置"

    # 检查 LLM API 密钥
    providers = []
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append("anthropic")
    if os.getenv("DASHSCOPE_API_KEY"):
        providers.append("dashscope")
    if os.getenv("OPENAI_API_KEY"):
        providers.append("openai")

    if not providers:
        issues.append("未设置任何 LLM API 密钥 (ANTHROPIC_API_KEY/DASHSCOPE_API_KEY/OPENAI_API_KEY)")
    else:
        info["llm_providers"] = providers

    # 检查项目路径
    if not PROJECT_ROOT.exists():
        issues.append(f"项目路径不存在: {PROJECT_ROOT}")
    else:
        info["project_path"] = str(PROJECT_ROOT)

    return {
        "status": "ready" if not issues else "not_ready",
        "issues": issues,
        "info": info
    }


async def run_analysis(ticker: str, date: str, depth: str = "medium") -> dict:
    """执行股票分析"""
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        # 配置
        config = DEFAULT_CONFIG.copy()
        depth_map = {"shallow": 1, "medium": 3, "deep": 5}
        config["max_debate_rounds"] = depth_map.get(depth, 3)
        config["max_risk_discuss_rounds"] = depth_map.get(depth, 3)

        # 检测可用的 LLM 提供商
        if os.getenv("ANTHROPIC_API_KEY"):
            config["llm_provider"] = "anthropic"
            config["deep_think_llm"] = "claude-sonnet-4-20250514"
            config["quick_think_llm"] = "claude-sonnet-4-20250514"
            config["backend_url"] = "https://api.anthropic.com/"
        elif os.getenv("DASHSCOPE_API_KEY"):
            config["llm_provider"] = "dashscope"
            config["deep_think_llm"] = "qwen-plus"
            config["quick_think_llm"] = "qwen-plus"
            config["backend_url"] = "https://dashscope.aliyuncs.com/api/v1"
        elif os.getenv("OPENAI_API_KEY"):
            config["llm_provider"] = "openai"
            config["deep_think_llm"] = "gpt-4o"
            config["quick_think_llm"] = "gpt-4o-mini"
            config["backend_url"] = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        else:
            return {"error": "未配置任何 LLM API 密钥"}

        # 创建结果目录
        results_dir = PROJECT_ROOT / "results" / ticker / date
        results_dir.mkdir(parents=True, exist_ok=True)
        report_dir = results_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        # 初始化
        ticker_full = get_ticker_suffix(ticker)
        graph = TradingAgentsGraph(
            ["market", "social", "news", "fundamentals"],
            config=config,
            debug=False
        )

        # 创建初始状态
        init_state = graph.propagator.create_initial_state(ticker_full, date)
        init_state["previous_decision_reflection"] = ""
        args = graph.propagator.get_graph_args()

        # 执行分析
        final_state = None
        for chunk in graph.graph.stream(init_state, **args):
            final_state = chunk

        if not final_state:
            return {"error": "分析未返回结果"}

        # 提取结果
        signal = graph.process_signal(final_state.get("final_trade_decision", ""))

        # 保存报告
        reports = {}
        for key in ["market_report", "sentiment_report", "news_report",
                    "fundamentals_report", "final_trade_decision",
                    "consolidation_report", "trader_investment_plan"]:
            content = final_state.get(key, "")
            if content:
                report_file = report_dir / f"{key}.md"
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(content)
                reports[key] = str(report_file)

        return {
            "ticker": ticker,
            "ticker_full": ticker_full,
            "date": date,
            "signal": signal,
            "depth": depth,
            "reports_dir": str(report_dir),
            "reports": reports,
            "consolidation_summary": final_state.get("consolidation_report", "")[:3000],
            "final_decision": final_state.get("final_trade_decision", "")[:1500]
        }

    except Exception as e:
        return {"error": str(e)}


def read_report_file(ticker: str, date: str, report_type: str) -> str:
    """读取指定的报告文件"""
    report_map = {
        "技术面": "market_report.md",
        "market": "market_report.md",
        "资金面": "sentiment_report.md",
        "sentiment": "sentiment_report.md",
        "新闻": "news_report.md",
        "news": "news_report.md",
        "基本面": "fundamentals_report.md",
        "fundamentals": "fundamentals_report.md",
        "综合": "consolidation_report.md",
        "consolidation": "consolidation_report.md",
        "决策": "final_trade_decision.md",
        "decision": "final_trade_decision.md",
        "交易计划": "trader_investment_plan.md",
        "trader": "trader_investment_plan.md",
    }

    filename = report_map.get(report_type.lower(), f"{report_type}.md")
    report_path = PROJECT_ROOT / "results" / ticker / date / "reports" / filename

    if report_path.exists():
        return report_path.read_text(encoding="utf-8")
    else:
        # 尝试查找最近的报告
        results_dir = PROJECT_ROOT / "results" / ticker
        if results_dir.exists():
            dates = sorted([d.name for d in results_dir.iterdir() if d.is_dir()], reverse=True)
            if dates:
                latest_report = results_dir / dates[0] / "reports" / filename
                if latest_report.exists():
                    return f"[注: 返回最近日期 {dates[0]} 的报告]\n\n" + latest_report.read_text(encoding="utf-8")
        return f"报告不存在: {report_path}"


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的工具"""
    return [
        Tool(
            name="analyze_stock",
            description="执行 A 股个股深度分析。分析包含技术面、基本面、资金面、新闻面，最终给出 BUY/SELL/HOLD 投资建议。分析耗时约 5-15 分钟。",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "股票代码（6位数字，如 600036）或股票名称（如 招商银行、茅台）"
                    },
                    "date": {
                        "type": "string",
                        "description": "分析日期，格式 YYYY-MM-DD，默认今天"
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["shallow", "medium", "deep"],
                        "description": "分析深度：shallow(快速3-5分钟)、medium(标准5-8分钟)、deep(深度8-15分钟)"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="resolve_ticker",
            description="将股票名称转换为股票代码。支持简称（如茅台→600519、招行→600036）",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "股票名称或简称"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="check_analysis_env",
            description="检查 A 股分析系统的运行环境是否配置正确",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="read_stock_report",
            description="读取已生成的股票分析报告",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "股票代码（6位数字）"
                    },
                    "date": {
                        "type": "string",
                        "description": "分析日期，格式 YYYY-MM-DD"
                    },
                    "report_type": {
                        "type": "string",
                        "enum": ["技术面", "资金面", "新闻", "基本面", "综合", "决策", "交易计划"],
                        "description": "报告类型"
                    }
                },
                "required": ["ticker", "report_type"]
            }
        ),
        Tool(
            name="list_analysis_history",
            description="列出某只股票的历史分析记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "股票代码（6位数字）"
                    }
                },
                "required": ["ticker"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """处理工具调用"""

    if name == "analyze_stock":
        ticker = arguments.get("ticker", "")
        date = arguments.get("date", datetime.now().strftime("%Y-%m-%d"))
        depth = arguments.get("depth", "medium")

        # 如果是股票名称，先转换为代码
        if not ticker.isdigit():
            resolved = resolve_ticker(ticker)
            if "error" in resolved:
                return [TextContent(type="text", text=json.dumps(resolved, ensure_ascii=False))]
            ticker = resolved["ticker"]

        # 验证代码格式
        if not re.match(r'^\d{6}$', ticker):
            return [TextContent(type="text", text=json.dumps({
                "error": f"无效的股票代码: {ticker}，请使用6位数字代码"
            }, ensure_ascii=False))]

        # 执行分析
        result = await run_analysis(ticker, date, depth)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "resolve_ticker":
        name_input = arguments.get("name", "")
        result = resolve_ticker(name_input)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "check_analysis_env":
        result = check_environment()
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "read_stock_report":
        ticker = arguments.get("ticker", "")
        date = arguments.get("date", "")
        report_type = arguments.get("report_type", "综合")

        # 如果没有指定日期，使用最近的
        if not date:
            results_dir = PROJECT_ROOT / "results" / ticker
            if results_dir.exists():
                dates = sorted([d.name for d in results_dir.iterdir() if d.is_dir()], reverse=True)
                date = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")

        content = read_report_file(ticker, date, report_type)
        return [TextContent(type="text", text=content)]

    elif name == "list_analysis_history":
        ticker = arguments.get("ticker", "")
        results_dir = PROJECT_ROOT / "results" / ticker

        if not results_dir.exists():
            return [TextContent(type="text", text=json.dumps({
                "ticker": ticker,
                "history": [],
                "message": "暂无分析记录"
            }, ensure_ascii=False))]

        history = []
        for date_dir in sorted(results_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                reports = list((date_dir / "reports").glob("*.md")) if (date_dir / "reports").exists() else []
                history.append({
                    "date": date_dir.name,
                    "reports_count": len(reports),
                    "reports": [r.stem for r in reports]
                })

        return [TextContent(type="text", text=json.dumps({
            "ticker": ticker,
            "history": history[:10]  # 最近10条
        }, ensure_ascii=False, indent=2))]

    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]


async def main():
    """主函数"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
