"""
Chatbot 报告查询工具

提供历史分析报告的查询、读取和对比功能。
"""
from typing import Annotated, Optional, List
from pathlib import Path
from langchain_core.tools import tool
import os
import logging

logger = logging.getLogger(__name__)

# 获取项目根目录
def get_project_root() -> Path:
    """获取项目根目录"""
    # 从当前文件向上查找，直到找到 results 目录或 .git 目录
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "results").exists() or (parent / ".git").exists():
            return parent
    # 默认返回工作目录
    return Path.cwd()


# 报告类型映射（中文 -> 文件名）
REPORT_TYPE_MAP = {
    # 综合类
    "综合": "consolidation_report",
    "研报": "consolidation_report",
    "综合研报": "consolidation_report",
    "综合报告": "consolidation_report",
    # 基本面
    "基本面": "fundamentals_report",
    "基本面报告": "fundamentals_report",
    "fundamentals": "fundamentals_report",
    # 技术面
    "技术": "market_report",
    "技术分析": "market_report",
    "技术面": "market_report",
    "market": "market_report",
    # 新闻
    "新闻": "news_report",
    "舆情": "news_report",
    "新闻舆情": "news_report",
    "news": "news_report",
    # 情绪
    "情绪": "sentiment_report",
    "情绪分析": "sentiment_report",
    "社交": "sentiment_report",
    "sentiment": "sentiment_report",
    # 投资计划
    "投资计划": "investment_plan",
    "投资": "investment_plan",
    # 交易计划
    "交易计划": "trader_investment_plan",
    "交易": "trader_investment_plan",
    "trader": "trader_investment_plan",
    # 最终决策
    "决策": "final_trade_decision",
    "最终决策": "final_trade_decision",
    "final": "final_trade_decision",
    # 反思
    "反思": "reflection_report",
    "历史反思": "reflection_report",
    "reflection": "reflection_report",
}

# 报告类型友好名称
REPORT_DISPLAY_NAMES = {
    "consolidation_report": "综合研报",
    "fundamentals_report": "基本面报告",
    "market_report": "技术分析报告",
    "news_report": "新闻舆情报告",
    "sentiment_report": "情绪分析报告",
    "investment_plan": "投资计划",
    "trader_investment_plan": "交易计划",
    "final_trade_decision": "最终决策",
    "reflection_report": "历史反思报告",
}


@tool
def list_available_reports(
    stock_code: Annotated[str, "股票代码，如 600036, 300300"]
) -> str:
    """
    列出某只股票的所有历史分析报告，按日期倒序排列。
    可以看到每个日期有哪些类型的报告可供查看。

    示例：
    - list_available_reports("600036") -> 列出招商银行所有历史报告
    - list_available_reports("300300") -> 列出海峡创新所有历史报告
    """
    project_root = get_project_root()
    results_dir = project_root / "results" / stock_code

    if not results_dir.exists():
        return f"未找到股票 {stock_code} 的历史分析报告。\n\n提示：请先对该股票运行完整分析以生成报告。"

    reports = []
    date_dirs = sorted(
        [d for d in results_dir.iterdir() if d.is_dir() and d.name[0].isdigit()],
        key=lambda x: x.name,
        reverse=True
    )

    if not date_dirs:
        return f"未找到股票 {stock_code} 的分析报告。\n\n提示：请先对该股票运行完整分析以生成报告。"

    for date_dir in date_dirs[:10]:  # 最多显示10个日期
        report_dir = date_dir / "reports"
        if report_dir.exists():
            files = []
            for f in sorted(report_dir.glob("*.md")):
                display_name = REPORT_DISPLAY_NAMES.get(f.stem, f.stem)
                files.append(display_name)
            if files:
                reports.append(f"📅 **{date_dir.name}**\n   {', '.join(files)}")

    if not reports:
        return f"未找到股票 {stock_code} 的分析报告。"

    return f"**{stock_code} 历史分析报告**\n\n" + "\n\n".join(reports)


@tool
def get_analysis_report(
    stock_code: Annotated[str, "股票代码，如 600036, 300300"],
    report_type: Annotated[str, "报告类型：综合/基本面/技术/新闻/决策/反思"] = "综合",
    analysis_date: Annotated[str, "分析日期 YYYY-MM-DD 格式，留空返回最新报告"] = ""
) -> str:
    """
    获取指定股票的历史分析报告内容。

    报告类型说明：
    - 综合/研报：综合研报（推荐，最完整的分析）
    - 基本面：基本面分析报告
    - 技术：技术分析报告
    - 新闻：新闻舆情报告
    - 情绪：情绪分析报告
    - 决策：最终交易决策
    - 反思：历史决策反思报告

    示例：
    - get_analysis_report("600036") -> 返回招商银行最新综合研报
    - get_analysis_report("600036", "基本面") -> 返回基本面报告
    - get_analysis_report("600036", "综合", "2026-01-10") -> 返回指定日期的报告
    """
    project_root = get_project_root()
    results_dir = project_root / "results" / stock_code

    if not results_dir.exists():
        return f"未找到股票 {stock_code} 的历史分析报告。\n\n提示：请使用 list_available_reports 工具查看可用的报告。"

    # 映射报告类型
    report_name = REPORT_TYPE_MAP.get(report_type, REPORT_TYPE_MAP.get(report_type.lower(), "consolidation_report"))

    # 确定日期目录
    if analysis_date:
        # 标准化日期格式
        date_str = analysis_date.replace("/", "-")
        date_dir = results_dir / date_str
        if not date_dir.exists():
            # 尝试查找匹配的日期
            matching = [d for d in results_dir.iterdir() if d.is_dir() and date_str in d.name]
            if matching:
                date_dir = matching[0]
            else:
                return f"未找到 {stock_code} 在 {analysis_date} 的分析报告。\n\n请使用 list_available_reports 查看可用日期。"
    else:
        # 获取最新日期
        date_dirs = sorted(
            [d for d in results_dir.iterdir() if d.is_dir() and d.name[0].isdigit()],
            key=lambda x: x.name,
            reverse=True
        )
        if not date_dirs:
            return f"未找到 {stock_code} 的分析报告。"
        date_dir = date_dirs[0]

    # 读取报告
    report_path = date_dir / "reports" / f"{report_name}.md"
    if not report_path.exists():
        # 列出可用的报告类型
        available_reports = []
        reports_dir = date_dir / "reports"
        if reports_dir.exists():
            for f in reports_dir.glob("*.md"):
                display_name = REPORT_DISPLAY_NAMES.get(f.stem, f.stem)
                available_reports.append(display_name)

        return (
            f"未找到 {stock_code} 在 {date_dir.name} 的{report_type}报告。\n\n"
            f"该日期可用的报告类型：{', '.join(available_reports) if available_reports else '无'}"
        )

    try:
        content = report_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"读取报告失败: {e}")
        return f"读取报告失败: {str(e)}"

    # 获取报告的友好名称
    display_name = REPORT_DISPLAY_NAMES.get(report_name, report_type)

    # 截断过长内容（LLM token 限制）
    max_length = 6000
    if len(content) > max_length:
        content = content[:max_length] + "\n\n... (报告内容过长，已截断。如需完整内容，请直接查看文件。)"

    return f"**{stock_code} {display_name}** ({date_dir.name})\n\n{content}"


@tool
def compare_reports(
    stock_code: Annotated[str, "股票代码，如 600036"],
    date1: Annotated[str, "第一个日期 YYYY-MM-DD"],
    date2: Annotated[str, "第二个日期 YYYY-MM-DD"]
) -> str:
    """
    对比同一股票在不同日期的分析报告，提取关键结论的变化。
    适合追踪分析结论的演变和验证历史预测的准确性。

    示例：
    - compare_reports("600036", "2026-01-06", "2026-01-10") -> 对比两次分析的变化
    """
    project_root = get_project_root()
    results_dir = project_root / "results" / stock_code

    if not results_dir.exists():
        return f"未找到股票 {stock_code} 的历史分析报告。"

    summaries = []
    for date in [date1, date2]:
        date_str = date.replace("/", "-")
        report_path = results_dir / date_str / "reports" / "consolidation_report.md"

        if report_path.exists():
            try:
                content = report_path.read_text(encoding="utf-8")

                # 提取执行摘要部分
                summary = ""
                if "## 执行摘要" in content:
                    parts = content.split("## 执行摘要")
                    if len(parts) > 1:
                        summary_section = parts[1].split("##")[0]
                        summary = summary_section.strip()[:1000]
                elif "# 执行摘要" in content:
                    parts = content.split("# 执行摘要")
                    if len(parts) > 1:
                        summary_section = parts[1].split("#")[0]
                        summary = summary_section.strip()[:1000]
                else:
                    # 取前1000字符作为摘要
                    summary = content[:1000]

                summaries.append(f"### 📅 {date}\n\n{summary}")
            except Exception as e:
                summaries.append(f"### 📅 {date}\n\n读取失败: {str(e)}")
        else:
            # 检查是否有其他报告
            date_dir = results_dir / date_str
            if date_dir.exists():
                reports_dir = date_dir / "reports"
                if reports_dir.exists():
                    available = [f.stem for f in reports_dir.glob("*.md")]
                    summaries.append(f"### 📅 {date}\n\n无综合研报，但有其他报告：{', '.join(available)}")
                else:
                    summaries.append(f"### 📅 {date}\n\n无报告")
            else:
                summaries.append(f"### 📅 {date}\n\n未找到该日期的分析")

    return f"**{stock_code} 报告对比**\n\n" + "\n\n---\n\n".join(summaries)


# 导出工具列表
REPORT_TOOLS = [
    list_available_reports,
    get_analysis_report,
    compare_reports,
]


def load_report_tools():
    """加载报告查询工具"""
    return REPORT_TOOLS
