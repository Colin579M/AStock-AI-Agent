"""
增强版 Chatbot

在 SimpleChatbot 基础上增加：
- 实体解析（股票名称→代码，日期表达→具体日期）
- 上下文记忆（记住当前讨论的股票）
- 指代消解（"它的PE"→当前股票的PE）
"""
import re
import logging
from typing import Optional, List, Generator
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from .tools.registry import load_all_tools
from .config import get_chatbot_config
from .context.entity_resolver import EntityResolver, get_entity_resolver
from .context.state import ConversationState
from tradingagents.graph.llm_factory import create_llm

logger = logging.getLogger(__name__)


ENHANCED_SYSTEM_PROMPT = """你是一个专业的A股投研助手，可以帮助用户查询股票数据和分析市场。

你可以使用多种工具来获取股票数据，包括：
- 基本信息、估值指标、资金流向、新闻、基本面数据
- 技术分析、财务指标、龙虎榜、北向资金等

使用指南：
- 股票代码使用6位数字格式（如 600036、000001）
- 如果用户提到股票名称，请用工具确认代码
- 回答要简洁明了，重点突出关键数据
- 今天是 {today}

{context_hint}

请用中文回答用户的问题。"""


class EnhancedChatbot:
    """
    增强版 Chatbot

    支持实体解析和上下文记忆。
    """

    def __init__(self, config: Optional[dict] = None):
        """
        初始化 Chatbot

        Args:
            config: 可选配置覆盖
        """
        self.config = get_chatbot_config(config)
        self.tools = load_all_tools()
        self.messages: List = []

        # 实体解析器
        self.entity_resolver = get_entity_resolver()

        # 对话状态
        self.state = ConversationState()

        # 创建 LLM
        self.llm = create_llm(self.config)

        # 创建 Agent（缓存以避免重复创建）
        self._agent = None
        self._agent_context_key = None  # 用于检测上下文变化

        logger.info(f"EnhancedChatbot 初始化完成，加载了 {len(self.tools)} 个工具")

    def _get_agent(self):
        """获取或创建 Agent（带缓存）"""
        # 计算当前上下文的 key
        context_key = (
            self.state.current_ticker,
            self.state.current_date,
            datetime.now().strftime("%Y-%m-%d")
        )

        # 如果上下文未变化，复用已有 Agent
        if self._agent is not None and self._agent_context_key == context_key:
            return self._agent

        # 构建上下文提示
        context_hint = self._build_context_hint()

        system_prompt = ENHANCED_SYSTEM_PROMPT.format(
            today=datetime.now().strftime("%Y-%m-%d"),
            context_hint=context_hint
        )

        self._agent = create_react_agent(
            self.llm,
            self.tools,
            prompt=system_prompt,
        )
        self._agent_context_key = context_key

        return self._agent

    def _build_context_hint(self) -> str:
        """构建上下文提示"""
        hints = []

        if self.state.current_ticker:
            hints.append(f"当前讨论的股票: {self.state.current_ticker}")

        if self.state.current_date:
            hints.append(f"分析日期: {self.state.current_date}")

        if hints:
            return "上下文信息：\n" + "\n".join(f"- {h}" for h in hints)
        return ""

    def _preprocess_message(self, message: str) -> str:
        """
        预处理用户消息

        - 解析实体
        - 处理指代（它、这只股票）
        - 更新状态

        Args:
            message: 原始消息

        Returns:
            处理后的消息
        """
        processed = message

        # 1. 提取实体
        entities = self.entity_resolver.extract_entities(message)

        # 2. 更新状态中的股票
        if entities["tickers"]:
            # 使用第一个提到的股票作为当前股票
            self.state.update_ticker(entities["tickers"][0])

        # 3. 更新日期
        if entities["dates"]:
            self.state.update_date(entities["dates"][0])

        # 4. 处理指代消解（只有在没有明确提到股票时才替换）
        if self.state.current_ticker and not entities["tickers"]:
            pronoun_patterns = [
                (r'它的', f'{self.state.current_ticker}的'),
                (r'这只股票', self.state.current_ticker),
                (r'该股', self.state.current_ticker),
                (r'这支股票', self.state.current_ticker),
            ]

            for pattern, replacement in pronoun_patterns:
                if re.search(pattern, processed):
                    processed = re.sub(pattern, replacement, processed)
                    logger.debug(f"指代消解: {pattern} → {replacement}")

        # 5. 解析股票名称为代码
        # 查找可能的股票名称并替换为代码
        for name, code in self.entity_resolver._stock_cache.items():
            if name in processed and code not in processed:
                # 记录但不替换原文，让 LLM 自己处理
                self.state.update_ticker(code)

        return processed

    def chat(self, message: str) -> str:
        """
        处理用户消息，返回回答

        Args:
            message: 用户消息

        Returns:
            str: 助手回答
        """
        try:
            # 预处理消息
            processed_message = self._preprocess_message(message)
            logger.debug(f"处理后消息: {processed_message}")

            # 增加轮数
            self.state.increment_turn()

            # 获取 Agent（每次可能因上下文更新而重建）
            agent = self._get_agent()

            # 构建输入
            input_messages = self.messages + [HumanMessage(content=processed_message)]

            # 调用 Agent
            result = agent.invoke(
                {"messages": input_messages},
                {"recursion_limit": self.config.get("max_iterations", 10)}
            )

            # 提取回答
            response_messages = result.get("messages", [])
            response = "抱歉，我无法处理这个请求。"

            if response_messages:
                for msg in reversed(response_messages):
                    if isinstance(msg, AIMessage) and msg.content:
                        response = msg.content
                        break

            # 更新历史
            self.messages.append(HumanMessage(content=message))
            self.messages.append(AIMessage(content=response))

            # 限制历史长度
            max_history = self.config.get("max_history_messages", 20)
            if len(self.messages) > max_history:
                self.messages = self.messages[-max_history:]

            return response

        except Exception as e:
            logger.error(f"EnhancedChatbot 处理消息失败: {e}")
            return f"处理请求时出错: {str(e)}"

    def chat_stream(self, message: str) -> Generator[str, None, None]:
        """
        流式处理用户消息

        Args:
            message: 用户消息

        Yields:
            str: 回答片段
        """
        response = self.chat(message)
        yield response

    def clear_history(self):
        """清空对话历史和状态"""
        self.messages = []
        self.state.reset()
        logger.info("对话历史和状态已清空")

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

    def get_context(self) -> dict:
        """
        获取当前上下文

        Returns:
            dict: 上下文信息
        """
        return {
            "current_ticker": self.state.current_ticker,
            "current_date": self.state.current_date,
            "mentioned_tickers": self.state.mentioned_tickers,
            "turn_count": self.state.turn_count
        }


def create_enhanced_chatbot(config: Optional[dict] = None) -> EnhancedChatbot:
    """
    创建增强版 Chatbot 实例（工厂函数）

    Args:
        config: 可选配置

    Returns:
        EnhancedChatbot: Chatbot 实例
    """
    return EnhancedChatbot(config)
