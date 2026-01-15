"""
简单 Chatbot 实现

使用 LangChain Agent 实现工具调用的对话机器人。
"""
import logging
from typing import Optional, List, Generator
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from .tools.registry import load_core_tools
from .config import get_chatbot_config
from tradingagents.graph.llm_factory import create_llm


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个专业的A股投研助手，可以帮助用户查询股票数据和分析市场。

你可以使用以下工具：
1. get_stock_basic_info - 获取股票基本信息（名称、行业、上市日期等）
2. get_stock_valuation - 获取股票估值指标（PE、PB、市值、换手率等）
3. get_stock_moneyflow - 获取资金流向（大单、中单、小单净流入）
4. get_market_news - 获取新闻联播经济要点
5. get_stock_fundamentals - 获取基本面综合数据（财报、指标、预告、分红）

使用指南：
- 当用户提到股票时，请使用正确的6位数字股票代码
- 常见股票代码：600036(招商银行)、600519(贵州茅台)、000001(平安银行)、300750(宁德时代)
- 如果用户只说股票名称，请先用 get_stock_basic_info 确认股票代码
- 回答要简洁明了，重点突出关键数据
- 今天是 {today}

请用中文回答用户的问题。"""


class SimpleChatbot:
    """
    简单 Chatbot

    使用 ReAct Agent 模式，支持工具调用的对话机器人。
    """

    def __init__(self, config: Optional[dict] = None):
        """
        初始化 Chatbot

        Args:
            config: 可选配置覆盖
        """
        self.config = get_chatbot_config(config)
        self.tools = load_core_tools()
        self.messages: List = []

        # 创建 LLM
        self.llm = create_llm(self.config)

        # 创建 Agent
        self.agent = self._create_agent()

        logger.info(f"SimpleChatbot 初始化完成，加载了 {len(self.tools)} 个工具")

    def _create_agent(self):
        """创建 ReAct Agent"""
        # 使用 langgraph 的 create_react_agent
        system_prompt = SYSTEM_PROMPT.format(today=datetime.now().strftime("%Y-%m-%d"))

        agent = create_react_agent(
            self.llm,
            self.tools,
            prompt=system_prompt,
        )

        return agent

    def chat(self, message: str) -> str:
        """
        处理用户消息，返回回答

        Args:
            message: 用户消息

        Returns:
            str: 助手回答
        """
        try:
            # 构建输入
            input_messages = self.messages + [HumanMessage(content=message)]

            # 调用 Agent
            result = self.agent.invoke(
                {"messages": input_messages},
                {"recursion_limit": self.config.get("max_iterations", 10)}
            )

            # 提取回答
            response_messages = result.get("messages", [])
            if response_messages:
                # 获取最后一条 AI 消息
                for msg in reversed(response_messages):
                    if isinstance(msg, AIMessage) and msg.content:
                        response = msg.content
                        break
                else:
                    response = "抱歉，我无法处理这个请求。"
            else:
                response = "抱歉，我无法处理这个请求。"

            # 更新历史（保留最近的消息）
            self.messages.append(HumanMessage(content=message))
            self.messages.append(AIMessage(content=response))

            # 限制历史长度
            max_history = self.config.get("max_history_messages", 20)
            if len(self.messages) > max_history:
                self.messages = self.messages[-max_history:]

            return response

        except Exception as e:
            logger.error(f"Chatbot 处理消息失败: {e}")
            return f"处理请求时出错: {str(e)}"

    def chat_stream(self, message: str) -> Generator[str, None, None]:
        """
        流式处理用户消息

        Args:
            message: 用户消息

        Yields:
            str: 回答片段
        """
        # Phase 1 简单实现，直接返回完整回答
        # Phase 4 将实现真正的流式输出
        response = self.chat(message)
        yield response

    def clear_history(self):
        """清空对话历史"""
        self.messages = []
        logger.info("对话历史已清空")

    def get_history(self) -> List[dict]:
        """
        获取对话历史

        Returns:
            List[dict]: 对话历史列表
        """
        history = []
        for msg in self.messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history


def create_chatbot(config: Optional[dict] = None) -> SimpleChatbot:
    """
    创建 Chatbot 实例（工厂函数）

    Args:
        config: 可选配置

    Returns:
        SimpleChatbot: Chatbot 实例
    """
    return SimpleChatbot(config)
