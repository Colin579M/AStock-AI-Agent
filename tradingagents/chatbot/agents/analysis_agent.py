"""
深度分析 Agent

使用大模型进行深度分析（估值分析、趋势分析等）。
"""
import logging
from typing import Optional

from .base_agent import BaseAgent
from ..tools.registry import load_analysis_tools
from tradingagents.graph.llm_factory import create_llm

logger = logging.getLogger(__name__)


ANALYSIS_SYSTEM_PROMPT = """你是一个专业的A股投研分析师，可以进行深度的股票分析和解读。

你可以使用多种工具获取数据：
- 基本信息、估值指标、资金流向
- 财务报表、财务指标、业绩预告
- 前十大股东、股东人数变化
- 北向资金、融资融券
- 龙虎榜、大宗交易、解禁计划
- 指数走势、PMI宏观数据
- 券商评级、业绩快报

常用指数代码（分析大盘/指数时使用 get_index_daily 工具）：
- 大盘/上证指数/沪指 → 000001.SH
- 深证成指/深指 → 399001.SZ
- 创业板指/创业板 → 399006.SZ
- 沪深300 → 000300.SH
- 上证50 → 000016.SH
- 中证500 → 000905.SH
- 科创50 → 000688.SH

分析要求：
1. **数据驱动**：基于真实数据进行分析，不要编造数据
2. **多维度分析**：从估值、基本面、资金面、技术面等多角度分析
3. **客观中立**：给出平衡的观点，指出优势和风险
4. **结构清晰**：使用标题和要点组织回答
5. **专业但易懂**：使用专业术语但解释清楚

输出格式建议：
- 使用 Markdown 格式
- 关键数据加粗
- 结论放在最后

今天是 {today}
股票代码使用6位数字格式，指数代码使用6位数字.交易所后缀格式（如000001.SH）。
请用中文回答。"""


class AnalysisAgent(BaseAgent):
    """
    深度分析 Agent

    使用大模型 + 分析工具集（19个），进行深度分析。
    """

    def _load_tools(self):
        """加载分析工具集（优化：从26个减到19个）"""
        return load_analysis_tools()

    def _create_llm(self):
        """创建大模型 LLM"""
        analysis_config = self.config.copy()
        analysis_config["llm_provider"] = self.config.get("analysis_llm_provider", "openai")
        analysis_config["llm_model"] = self.config.get("analysis_llm_model", "deepseek-chat")
        return create_llm(analysis_config)

    def _get_system_prompt(self) -> str:
        """获取深度分析系统提示"""
        return ANALYSIS_SYSTEM_PROMPT

    @property
    def recursion_limit(self) -> int:
        """深度分析允许更多迭代（优化：从50降到20减少LLM开销）"""
        return 20

    @property
    def error_message(self) -> str:
        """深度分析错误提示"""
        return "抱歉，无法完成分析。"


def create_analysis_agent(config: Optional[dict] = None) -> AnalysisAgent:
    """
    创建 AnalysisAgent 实例

    Args:
        config: 可选配置

    Returns:
        AnalysisAgent: Agent 实例
    """
    return AnalysisAgent(config)
