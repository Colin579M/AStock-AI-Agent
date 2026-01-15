"""
快速查询 Agent

使用小模型快速回答简单问题（价格、基本信息等）。
"""
import logging
from typing import Optional

from .base_agent import BaseAgent, TOOL_DISPLAY_NAMES
from ..config import get_chatbot_config
from ..tools.registry import load_quick_tools
from tradingagents.graph.llm_factory import create_llm

logger = logging.getLogger(__name__)


QUICK_SYSTEM_PROMPT = """你是一个A股数据查询助手，专门快速回答简单的股票数据问题。

你可以使用工具查询：
- 股票基本信息（名称、行业、上市日期）
- 估值指标（PE、PB、市值、换手率）
- 资金流向（主力净流入）
- 新闻联播要点
- 基本面数据
- 指数走势（使用 get_index_daily 工具）
- **排行榜数据**：涨幅榜、跌幅榜、成交额榜、换手率榜、资金流入榜、资金流出榜
- **热门股票**：人气榜、成交活跃股
- **连续上涨股票**：连涨3天/5天以上的股票

常用指数代码（查询大盘/指数时使用 get_index_daily 工具）：
- 大盘/上证指数/沪指 → 000001.SH
- 深证成指/深指 → 399001.SZ
- 创业板指/创业板 → 399006.SZ
- 沪深300 → 000300.SH

排行榜查询说明：
- 支持时间周期：今日、5日、10日、20日
- 支持市场筛选：全部、沪市、深市、创业板、科创板
- 默认返回前20名，可指定返回数量

**错别字纠正**（重要）：
用户可能输入错别字，你需要智能纠正：
- "毛台"、"贵州毛台" -> 贵州茅台 (600519)
- "宁得时代" -> 宁德时代 (300750)
- "比亚笛" -> 比亚迪 (002594)
- "招商银航" -> 招商银行 (600036)
- "东方财付" -> 东方财富 (300059)

回答要求：
- 简洁直接，不要过度解释
- 直接给出数据，避免冗长的开场白
- 如果用户问的是简单数据，直接返回数据即可
- 今天是 {today}

股票代码使用6位数字格式（如 600036、000001）。
指数代码使用6位数字.交易所后缀格式（如 000001.SH）。
请用中文回答。"""


class QuickAgent(BaseAgent):
    """
    快速查询 Agent

    使用小模型 + 精简工具集（8个），快速回答简单问题。
    """

    def _load_tools(self):
        """加载精简工具集（优化：从26个减到8个）"""
        return load_quick_tools()

    def _create_llm(self):
        """创建小模型 LLM"""
        quick_config = self.config.copy()
        quick_config["llm_provider"] = self.config.get("quick_llm_provider", "openai")
        quick_config["quick_think_llm"] = self.config.get("quick_llm_model", "deepseek-chat")
        return create_llm(quick_config, llm_type="quick")

    def _get_system_prompt(self) -> str:
        """获取快速查询系统提示"""
        return QUICK_SYSTEM_PROMPT

    @property
    def recursion_limit(self) -> int:
        """快速查询限制迭代次数（优化：从10降到5加速响应）"""
        return 5

    @property
    def error_message(self) -> str:
        """快速查询错误提示"""
        return "抱歉，无法获取数据。"


def create_quick_agent(config: Optional[dict] = None) -> QuickAgent:
    """
    创建 QuickAgent 实例

    Args:
        config: 可选配置

    Returns:
        QuickAgent: Agent 实例
    """
    return QuickAgent(config)


# 为了向后兼容，保留导出
__all__ = ["QuickAgent", "create_quick_agent", "TOOL_DISPLAY_NAMES"]
