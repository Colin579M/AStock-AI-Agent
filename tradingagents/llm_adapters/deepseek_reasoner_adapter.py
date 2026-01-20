"""
DeepSeek Reasoner API 适配器

为 TradingAgents 提供 DeepSeek Reasoner (thinking mode) 的 LangChain 兼容接口
正确处理 reasoning_content 字段以支持 tool calls

参考文档: https://api-docs.deepseek.com/guides/thinking_mode#tool-calls
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Union, Sequence, Iterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessageChunk
)
from langchain_core.outputs import ChatGeneration, ChatResult, ChatGenerationChunk
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.tools import BaseTool
from pydantic import Field, SecretStr

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


class ChatDeepSeekReasoner(BaseChatModel):
    """
    DeepSeek Reasoner (thinking mode) 的 LangChain 适配器

    关键特性：
    - 正确处理 reasoning_content 字段
    - 支持 tool calls 的多轮对话
    - 在同一轮对话中保留 reasoning_content
    """

    # 模型配置
    model: str = Field(default="deepseek-reasoner", description="DeepSeek 模型名称")
    api_key: Optional[SecretStr] = Field(default=None, description="DeepSeek API 密钥")
    base_url: str = Field(default="https://api.deepseek.com/v1", description="API 地址")
    temperature: float = Field(default=0.0, description="生成温度 (reasoner 模式固定为 0)")
    max_tokens: int = Field(default=8000, description="最大生成 token 数")
    timeout: int = Field(default=300, description="API 调用超时时间（秒）")

    # 工具配置
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="绑定的工具列表")
    tool_choice: Optional[str] = Field(default=None, description="工具选择策略")

    # 内部属性
    _client: Any = None

    def __init__(self, **kwargs):
        """初始化 DeepSeek Reasoner 客户端"""
        super().__init__(**kwargs)

        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not found. Please install it with: pip install openai"
            )

        # 设置 API 密钥
        api_key = self.api_key
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")

        if api_key is None:
            raise ValueError(
                "DeepSeek API key not found. Please set OPENAI_API_KEY or DEEPSEEK_API_KEY "
                "environment variable or pass api_key parameter."
            )

        # 初始化客户端
        key_value = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key

        self._client = OpenAI(
            api_key=key_value,
            base_url=self.base_url,
            timeout=self.timeout
        )

    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型"""
        return "deepseek-reasoner"

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], BaseTool]],
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> "ChatDeepSeekReasoner":
        """绑定工具到模型，返回新实例"""
        formatted_tools = []
        for tool in tools:
            if isinstance(tool, BaseTool):
                # 转换 LangChain 工具为 OpenAI 格式
                params = tool.args_schema.model_json_schema() if tool.args_schema else {"type": "object", "properties": {}}
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": params
                    }
                })
            elif isinstance(tool, dict):
                formatted_tools.append(tool)

        # 创建新实例
        new_instance = ChatDeepSeekReasoner(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            tools=formatted_tools,
            tool_choice=tool_choice or self.tool_choice,
        )
        return new_instance

    def _convert_messages_to_openai_format(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """
        将 LangChain 消息转换为 OpenAI/DeepSeek 格式

        关键：保留 AIMessage 中的 reasoning_content 字段
        """
        openai_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                openai_messages.append({
                    "role": "system",
                    "content": msg.content
                })
            elif isinstance(msg, HumanMessage):
                openai_messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif isinstance(msg, AIMessage):
                ai_msg = {
                    "role": "assistant",
                    "content": msg.content or ""
                }

                # 关键：保留 reasoning_content 字段（即使为空也必须传递！）
                # DeepSeek 要求：只要有 tool_calls，就必须有 reasoning_content 字段
                if "reasoning_content" in msg.additional_kwargs:
                    ai_msg["reasoning_content"] = msg.additional_kwargs["reasoning_content"]
                elif msg.tool_calls or msg.additional_kwargs.get("tool_calls"):
                    # 如果有 tool_calls 但没有 reasoning_content，添加空字符串
                    ai_msg["reasoning_content"] = ""

                # 处理 tool_calls
                if msg.tool_calls:
                    ai_msg["tool_calls"] = [
                        {
                            "id": tc["id"] if isinstance(tc, dict) else tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc["name"] if isinstance(tc, dict) else tc.get("name"),
                                "arguments": json.dumps(tc["args"] if isinstance(tc, dict) else tc.get("args", {}), ensure_ascii=False)
                            }
                        }
                        for i, tc in enumerate(msg.tool_calls)
                    ]
                # 兼容旧格式
                elif msg.additional_kwargs.get("tool_calls"):
                    ai_msg["tool_calls"] = msg.additional_kwargs["tool_calls"]

                openai_messages.append(ai_msg)
            elif isinstance(msg, ToolMessage):
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content
                })

        return openai_messages

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """生成响应"""
        openai_messages = self._convert_messages_to_openai_format(messages)

        # 调试：打印转换后的消息
        logger.info(f"DeepSeek Reasoner: 发送 {len(openai_messages)} 条消息")
        for i, msg in enumerate(openai_messages):
            role = msg.get("role", "unknown")
            has_rc = "reasoning_content" in msg
            has_tc = "tool_calls" in msg
            logger.info(f"  [{i}] {role}: reasoning_content={has_rc}, tool_calls={has_tc}")
            if role == "assistant" and has_tc and not has_rc:
                logger.error(f"  ⚠️ 错误: assistant 消息有 tool_calls 但没有 reasoning_content!")

        # 构建请求参数
        request_params = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": self.max_tokens,
        }

        # 添加工具（如果有）
        if self.tools:
            request_params["tools"] = self.tools
            if self.tool_choice:
                request_params["tool_choice"] = self.tool_choice

        if stop:
            request_params["stop"] = stop

        # 调用 API
        try:
            response = self._client.chat.completions.create(**request_params)
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            raise

        # 解析响应
        choice = response.choices[0]
        message = choice.message

        # 构建 AIMessage，保留 reasoning_content
        additional_kwargs = {}

        # 关键：保存 reasoning_content 到 additional_kwargs（即使为空也必须保存！）
        if hasattr(message, 'reasoning_content'):
            # reasoning_content 可能为空字符串，也必须保存
            additional_kwargs["reasoning_content"] = message.reasoning_content or ""
            logger.debug(f"保存 reasoning_content: {len(additional_kwargs['reasoning_content'])} chars")

        # 处理 tool_calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": json.loads(tc.function.arguments) if tc.function.arguments else {}
                })
            # 也保存原始格式到 additional_kwargs
            additional_kwargs["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]

        ai_message = AIMessage(
            content=message.content or "",
            tool_calls=tool_calls,
            additional_kwargs=additional_kwargs
        )

        # 构建返回结果
        generation = ChatGeneration(
            message=ai_message,
            generation_info={
                "finish_reason": choice.finish_reason,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
            }
        )

        return ChatResult(generations=[generation])

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """返回识别参数"""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
        }
