"""
Chatbot Graph

简化版：单一 Agent 处理所有查询，依赖 LLM 智能决策。
支持快捷命令和深度分析模式。
"""
import logging
from typing import Optional, List, Callable
from datetime import datetime

from langchain_core.messages import HumanMessage

from .agents.unified_agent import UnifiedAgent
from .context.entity_resolver import get_entity_resolver
from .context.state import ConversationState
from .config import get_chatbot_config
from .templates.analysis_templates import (
    QUICK_COMMANDS,
    build_analysis_menu,
    parse_dimension_selection,
)
from .templates.template_executor import TemplateExecutor

logger = logging.getLogger(__name__)


class ChatbotGraph:
    """
    Chatbot Graph（简化版）

    单一 Agent 架构，无需复杂路由。
    """

    def __init__(self, config: Optional[dict] = None):
        """
        初始化 Chatbot Graph

        Args:
            config: 可选配置覆盖
        """
        self.config = get_chatbot_config(config)

        # 初始化组件
        self.entity_resolver = get_entity_resolver()
        self.conversation_state = ConversationState()

        # 延迟初始化 Agent 和模板执行器
        self._agent: Optional[UnifiedAgent] = None
        self._template_executor: Optional[TemplateExecutor] = None

        # 深度分析状态追踪
        self._pending_analysis_stock: Optional[str] = None

        # 后台预热 A 股数据缓存
        self._prewarm_cache()

        logger.info("ChatbotGraph 初始化完成（统一 Agent 架构 + 深度分析）")

    def _prewarm_cache(self):
        """后台预热 A 股数据缓存（使用 tushare，更快）"""
        try:
            import threading
            def prewarm():
                try:
                    from tradingagents.dataflows.tushare_utils import get_all_stocks_daily
                    df = get_all_stocks_daily()
                    if df is not None and not df.empty:
                        logger.info(f"[tushare] 缓存预热完成: {len(df)} 只股票")
                except Exception as e:
                    logger.warning(f"tushare 缓存预热失败: {e}")
            thread = threading.Thread(target=prewarm, daemon=True)
            thread.start()
        except Exception as e:
            logger.warning(f"缓存预热启动失败: {e}")

    @property
    def agent(self) -> UnifiedAgent:
        """延迟加载 UnifiedAgent"""
        if self._agent is None:
            self._agent = UnifiedAgent(self.config)
            logger.info(f"UnifiedAgent 初始化完成，工具数量: {len(self._agent.tools)}")
        return self._agent

    @property
    def template_executor(self) -> TemplateExecutor:
        """延迟加载模板执行器"""
        if self._template_executor is None:
            self._template_executor = TemplateExecutor(self.agent)
            logger.info("TemplateExecutor 初始化完成")
        return self._template_executor

    def chat(self, message: str, history: Optional[List] = None) -> str:
        """
        便捷的聊天接口

        Args:
            message: 用户消息
            history: 历史消息

        Returns:
            str: 回答
        """
        # 1. 快速处理闲聊（不调用 LLM）
        chat_response = self._get_chat_response(message)
        if chat_response:
            return chat_response

        # 2. 检查快捷命令（如 /深度分析 茅台）
        quick_response = self._handle_quick_command(message)
        if quick_response:
            return quick_response

        # 3. 检查是否为深度分析请求
        deep_response = self._handle_deep_analysis_request(message)
        if deep_response:
            return deep_response

        # 4. 检查是否为维度选择（对之前的分析菜单的回复）
        dimension_response = self._handle_dimension_selection(message)
        if dimension_response:
            return dimension_response

        # 5. 使用统一 Agent 处理
        messages = []
        if history:
            messages.extend(history)

        return self.agent.run(message, messages)

    def chat_with_progress(
        self,
        message: str,
        history: Optional[List] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        带进度回调的聊天接口

        Args:
            message: 用户消息
            history: 历史消息
            progress_callback: 进度回调函数 (event_type, content)

        Returns:
            str: 回答
        """
        def emit(event_type: str, content: str):
            """发送进度事件"""
            if progress_callback:
                try:
                    progress_callback(event_type, content)
                except Exception as e:
                    logger.error(f"进度回调失败: {e}")

        # 1. 实体解析（可选，用于上下文追踪）
        entities = self.entity_resolver.extract_entities(message)
        ticker = entities["tickers"][0] if entities["tickers"] else None

        if ticker:
            self.conversation_state.update_ticker(ticker)
            emit("thinking", f"识别到股票: {ticker}")

        if entities["dates"]:
            self.conversation_state.update_date(entities["dates"][0])

        # 2. 快速处理闲聊（不调用 LLM）
        chat_response = self._get_chat_response(message)
        if chat_response:
            return chat_response

        # 3. 检查快捷命令（如 /深度分析 茅台）
        quick_response = self._handle_quick_command(message)
        if quick_response:
            return quick_response

        # 4. 检查是否为深度分析请求
        deep_response = self._handle_deep_analysis_request(message)
        if deep_response:
            return deep_response

        # 5. 检查是否为维度选择（对之前的分析菜单的回复）
        dimension_response = self._handle_dimension_selection(message)
        if dimension_response:
            return dimension_response

        # 6. 使用统一 Agent 处理（带进度回调）
        emit("thinking", "分析问题中...")

        messages = []
        if history:
            messages.extend(history)

        response = self.agent.run_with_progress(
            message,
            messages,
            emit
        )

        return response

    def _handle_quick_command(self, message: str) -> Optional[str]:
        """
        处理快捷命令（如 /深度分析 茅台）

        Args:
            message: 用户消息

        Returns:
            str 或 None: 分析结果或 None
        """
        message = message.strip()

        # 检查是否以 / 开头
        if not message.startswith("/"):
            return None

        # 解析命令和参数
        parts = message.split(maxsplit=1)
        command = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        # 查找匹配的快捷命令
        template_key = QUICK_COMMANDS.get(command)
        if not template_key:
            return None

        # 提取股票信息
        if arg:
            entities = self.entity_resolver.extract_entities(arg)
            ticker = entities["tickers"][0] if entities["tickers"] else None
            stock_name = arg.strip()
        else:
            # 尝试使用上下文中的股票
            ticker = self.conversation_state.current_ticker
            stock_name = ticker

        if not ticker and not stock_name:
            return f"请指定股票名称，例如：{command} 茅台"

        # 执行分析
        logger.info(f"执行快捷命令: {command} -> {template_key}, 股票: {stock_name}")
        return self.template_executor.execute_quick_command(
            template_key,
            ticker or stock_name,
            stock_name,
            None  # 无进度回调
        )

    def _handle_deep_analysis_request(self, message: str) -> Optional[str]:
        """
        检测并处理深度分析请求

        当用户说"深度分析"、"全面分析"等时，返回分析维度选择菜单。

        Args:
            message: 用户消息

        Returns:
            str 或 None: 分析菜单或 None
        """
        # 深度分析触发词
        triggers = ["深度分析", "全面分析", "详细分析", "帮我分析", "分析一下"]

        # 检查是否包含触发词
        if not any(t in message for t in triggers):
            return None

        # 提取股票信息
        entities = self.entity_resolver.extract_entities(message)
        ticker = entities["tickers"][0] if entities["tickers"] else None

        # 从消息中提取股票名称
        stock_name = None
        for t in triggers:
            if t in message:
                # 尝试提取触发词后面的内容作为股票名称
                idx = message.find(t)
                remaining = message[idx + len(t):].strip()
                if remaining:
                    stock_name = remaining
                    break

        if not ticker and not stock_name:
            # 尝试使用上下文中的股票
            if self.conversation_state.current_ticker:
                stock_name = self.conversation_state.current_ticker
            else:
                return "请告诉我您想分析哪只股票？例如：深度分析 茅台"

        # 保存待分析的股票，等待用户选择维度
        self._pending_analysis_stock = stock_name or ticker
        self.conversation_state.update_ticker(ticker or stock_name)

        # 返回分析菜单
        return build_analysis_menu(self._pending_analysis_stock)

    def _handle_dimension_selection(self, message: str) -> Optional[str]:
        """
        处理维度选择（用户对分析菜单的回复）

        Args:
            message: 用户消息

        Returns:
            str 或 None: 分析结果或 None
        """
        # 如果没有待分析的股票，跳过
        if not self._pending_analysis_stock:
            return None

        # 解析用户选择
        dimensions = parse_dimension_selection(message)

        if not dimensions:
            return None

        # 执行选定的分析维度
        stock_name = self._pending_analysis_stock
        self._pending_analysis_stock = None  # 清除状态

        logger.info(f"执行深度分析: {stock_name}, 维度: {dimensions}")
        return self.template_executor.execute_dimensions(
            dimensions,
            stock_name,
            stock_name,
            None  # 无进度回调
        )

    def _get_chat_response(self, message: str) -> Optional[str]:
        """
        获取闲聊回复（不调用 LLM）

        只处理明确的闲聊场景，其他返回 None 让 Agent 处理。

        Args:
            message: 用户消息

        Returns:
            str 或 None: 预设回复或 None
        """
        message_lower = message.lower().strip()

        # 只处理短消息的闲聊
        if len(message) > 15:
            return None

        # 问候
        if message_lower in ["你好", "您好", "hi", "hello", "嗨", "哈喽"]:
            return "您好！我是A股投资助手，可以查询股票数据、分析估值、查看资金流向等。请问有什么可以帮您的？"

        # 早晚问候
        if message_lower in ["早上好", "早"]:
            return "早上好！今天想了解哪只股票？"
        if message_lower in ["下午好"]:
            return "下午好！有什么可以帮您的？"
        if message_lower in ["晚上好"]:
            return "晚上好！需要查看今天的市场行情吗？"

        # 感谢
        if message_lower in ["谢谢", "感谢", "thanks", "多谢", "谢谢你"]:
            return "不客气！还有其他问题随时问我。"

        # 告别
        if message_lower in ["再见", "拜拜", "bye", "回见"]:
            return "再见！祝您投资顺利！"

        # 确认
        if message_lower in ["好的", "ok", "明白", "知道了", "收到", "好"]:
            return "好的，还有其他问题吗？"

        # 在吗
        if message_lower in ["在吗", "在不在", "在么"]:
            return "我在的，请问有什么可以帮您？"

        # 你是谁
        if message_lower in ["你是谁", "你是什么"]:
            return "我是A股投资助手，可以帮您查询股票信息、分析估值、查看资金流向等。"

        # 其他情况交给 Agent 处理
        return None


def create_chatbot_graph(config: Optional[dict] = None) -> ChatbotGraph:
    """
    创建 Chatbot Graph 实例

    Args:
        config: 可选配置

    Returns:
        ChatbotGraph: Graph 实例
    """
    return ChatbotGraph(config)
