"""
Agent 基类

提取 QuickAgent 和 AnalysisAgent 的公共逻辑。
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Callable
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from ..tools.registry import load_all_tools, load_quick_tools, load_analysis_tools
from ..config import get_chatbot_config
from tradingagents.graph.llm_factory import create_llm

logger = logging.getLogger(__name__)


# 工具名称映射（用于友好显示）
TOOL_DISPLAY_NAMES = {
    "get_stock_basic_info": "基本信息",
    "get_stock_valuation": "估值数据 (PE/PB/市值)",
    "get_stock_moneyflow": "资金流向",
    "get_market_news": "市场新闻",
    "get_stock_fundamentals": "基本面数据",
    "get_stock_finance": "财务报表",
    "get_financial_indicators": "财务指标",
    "get_stock_forecast": "业绩预告",
    "get_stock_dividend": "分红信息",
    "get_stock_pledge": "股权质押",
    "get_top_holders": "前十大股东",
    "get_shareholder_count": "股东人数",
    "get_northbound_flow": "北向资金",
    "get_margin_trading": "融资融券",
    "get_dragon_tiger": "龙虎榜",
    "get_block_trade": "大宗交易",
    "get_unlock_schedule": "解禁计划",
    "get_index_trend": "指数走势",
    "get_pmi_data": "PMI数据",
    "get_analyst_ratings": "券商评级",
    "get_express_report": "业绩快报",
    # 排行榜工具
    "get_stock_ranking": "排行榜数据",
    "get_hot_stocks_list": "热门股票",
    "get_continuous_rise_stocks": "连涨股票",
    # 报告查询工具
    "list_available_reports": "历史报告列表",
    "get_analysis_report": "分析报告",
    "compare_reports": "报告对比",
}


class BaseAgent(ABC):
    """
    Agent 基类

    定义 Agent 的通用接口和行为。
    """

    def __init__(self, config: Optional[dict] = None):
        """
        初始化 Agent

        Args:
            config: 可选配置覆盖
        """
        self.config = get_chatbot_config(config)
        self.llm = self._create_llm()
        self.tools = self._load_tools()
        self.agent = self._create_agent()

        logger.debug(f"{self.__class__.__name__} 初始化完成，使用 {len(self.tools)} 个工具")

    def _load_tools(self) -> List:
        """
        加载工具集（子类可覆盖以使用不同工具集）

        Returns:
            List[BaseTool]: 工具列表
        """
        return load_all_tools()

    @abstractmethod
    def _create_llm(self):
        """创建 LLM 实例（子类实现）"""
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """获取系统提示（子类实现）"""
        pass

    @property
    def recursion_limit(self) -> int:
        """获取迭代限制（子类可覆盖）"""
        return 10

    @property
    def error_message(self) -> str:
        """获取错误提示（子类可覆盖）"""
        return "抱歉，无法处理请求。"

    def _create_agent(self):
        """创建 ReAct Agent"""
        system_prompt = self._get_system_prompt().format(
            today=datetime.now().strftime("%Y-%m-%d")
        )

        agent = create_react_agent(
            self.llm,
            self.tools,
            prompt=system_prompt,
        )

        return agent

    def run(self, query: str, history: Optional[List] = None) -> str:
        """
        执行查询

        Args:
            query: 用户查询
            history: 可选的历史消息

        Returns:
            str: 查询结果
        """
        try:
            messages = []
            if history:
                messages.extend(history)
            messages.append(HumanMessage(content=query))

            result = self.agent.invoke(
                {"messages": messages},
                {"recursion_limit": self.recursion_limit}
            )

            response_messages = result.get("messages", [])
            for msg in reversed(response_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    return msg.content

            return self.error_message

        except Exception as e:
            logger.error(f"{self.__class__.__name__} 执行失败: {e}")
            return f"处理失败: {str(e)}"

    def run_with_progress(
        self,
        query: str,
        history: Optional[List] = None,
        emit: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        带进度回调的执行

        Args:
            query: 用户查询
            history: 可选的历史消息
            emit: 进度回调函数 (event_type, content)

        Returns:
            str: 查询结果
        """
        try:
            messages = []
            if history:
                messages.extend(history)
            messages.append(HumanMessage(content=query))

            final_response = None
            seen_tools = set()

            for chunk in self.agent.stream(
                {"messages": messages},
                {"recursion_limit": self.recursion_limit}
            ):
                chunk_messages = self._extract_messages_from_chunk(chunk)

                for msg in chunk_messages:
                    # 检测工具调用开始
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                            tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                            if tool_name and tool_name not in seen_tools:
                                seen_tools.add(tool_name)
                                display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                # 诊断日志：详细记录工具调用
                                logger.info(f"[诊断] LLM 调用工具: {tool_name}, 参数: {tool_args}")
                                if emit:
                                    emit("tool", f"获取{display_name}...")

                    # 检测工具返回
                    if isinstance(msg, ToolMessage):
                        if emit:
                            emit("tool", "✓ 数据已获取")

                    # 检测最终回答
                    if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                        final_response = msg.content

            # 只有在 stream 没有获取到最终回答时才调用 invoke
            if not final_response:
                if emit:
                    emit("thinking", "正在生成回答...")
                result = self.agent.invoke(
                    {"messages": messages},
                    {"recursion_limit": self.recursion_limit}
                )
                response_messages = result.get("messages", [])
                for msg in reversed(response_messages):
                    if isinstance(msg, AIMessage) and msg.content:
                        final_response = msg.content
                        break

            return final_response or self.error_message

        except Exception as e:
            logger.error(f"{self.__class__.__name__} 执行失败: {e}")
            return f"处理失败: {str(e)}"

    def _extract_messages_from_chunk(self, chunk: dict) -> List:
        """从 stream chunk 中提取消息"""
        if "messages" in chunk:
            return chunk["messages"]
        elif "agent" in chunk and "messages" in chunk["agent"]:
            return chunk["agent"]["messages"]
        elif "tools" in chunk and "messages" in chunk["tools"]:
            return chunk["tools"]["messages"]
        return []
