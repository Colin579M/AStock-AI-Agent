"""
OpenAI Responses API 适配器
为 TradingAgents 提供 OpenAI Responses API 的 LangChain 兼容接口
支持 GPT-5.2 的 Chain of Thought 传递和更好的上下文管理
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Union, Sequence

logger = logging.getLogger(__name__)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable
from pydantic import Field, SecretStr

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


class ChatOpenAIResponses(BaseChatModel):
    """OpenAI Responses API 的 LangChain 适配器"""

    # 模型配置
    model: str = Field(default="gpt-5.2", description="OpenAI 模型名称")
    api_key: Optional[SecretStr] = Field(default=None, description="OpenAI API 密钥")
    base_url: Optional[str] = Field(default=None, description="自定义 API 地址")
    reasoning_effort: str = Field(default="medium", description="推理深度: none, low, medium, high, xhigh")
    temperature: Optional[float] = Field(default=None, description="生成温度 (仅 reasoning=none 时有效)")
    max_tokens: int = Field(default=4000, description="最大生成token数")
    timeout: int = Field(default=120, description="API 调用超时时间（秒）")

    # 工具配置
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="绑定的工具列表")
    tool_choice: Optional[str] = Field(default=None, description="工具选择策略")

    # 内部属性
    _client: Any = None
    _previous_response_id: Optional[str] = None

    def __init__(self, **kwargs):
        """初始化 OpenAI Responses 客户端"""
        super().__init__(**kwargs)

        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not found. Please install it with: pip install openai"
            )

        # 设置API密钥
        api_key = self.api_key
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")

        if api_key is None:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        # 初始化客户端
        key_value = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key

        client_kwargs = {
            "api_key": key_value,
            "timeout": self.timeout  # 添加超时设置
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self._client = OpenAI(**client_kwargs)

    @property
    def _llm_type(self) -> str:
        """返回LLM类型"""
        return "openai-responses"

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], BaseTool]],
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> "ChatOpenAIResponses":
        """绑定工具到模型，返回新实例"""
        formatted_tools = []
        for tool in tools:
            if isinstance(tool, BaseTool):
                # 转换 LangChain 工具为 Responses API 格式
                # 注意：Responses API 格式与 Chat Completions 不同
                # Responses API: {"type": "function", "name": ..., "description": ..., "parameters": ...}
                # Chat Completions: {"type": "function", "function": {"name": ..., ...}}
                params = tool.args_schema.model_json_schema() if tool.args_schema else {"type": "object", "properties": {}}
                # 清理 schema 中不需要的字段
                if "title" in params:
                    del params["title"]
                if "description" in params:
                    del params["description"]
                tool_schema = {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": params
                }
                formatted_tools.append(tool_schema)
            elif isinstance(tool, dict):
                formatted_tools.append(tool)

        # 创建新实例并复制配置
        return ChatOpenAIResponses(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            reasoning_effort=self.reasoning_effort,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=formatted_tools,
            tool_choice=tool_choice,
        )

    def _convert_messages_to_responses_format(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """将 LangChain 消息格式转换为 Responses API 格式"""
        responses_messages = []

        for message in messages:
            if isinstance(message, SystemMessage):
                role = "developer"  # Responses API 使用 "developer" 而不是 "system"
                responses_messages.append({"role": role, "content": message.content})
            elif isinstance(message, HumanMessage):
                responses_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, ToolMessage):
                # 工具结果消息
                responses_messages.append({
                    "type": "function_call_output",
                    "call_id": message.tool_call_id,
                    "output": message.content if isinstance(message.content, str) else json.dumps(message.content)
                })
            elif isinstance(message, AIMessage):
                # 检查是否有工具调用
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # 先添加助手消息内容（如果有）
                    if message.content:
                        responses_messages.append({"role": "assistant", "content": message.content})
                    # 添加工具调用
                    for tool_call in message.tool_calls:
                        responses_messages.append({
                            "type": "function_call",
                            "call_id": tool_call.get("id", ""),
                            "name": tool_call.get("name", ""),
                            "arguments": json.dumps(tool_call.get("args", {})) if isinstance(tool_call.get("args"), dict) else tool_call.get("args", "{}")
                        })
                else:
                    responses_messages.append({"role": "assistant", "content": message.content})
            else:
                content = message.content
                if isinstance(content, list):
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content += item.get("text", "")
                        elif isinstance(item, str):
                            text_content += item
                    content = text_content
                responses_messages.append({"role": "user", "content": content})

        return responses_messages

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """调用 Responses API 生成响应"""

        # 转换消息格式
        responses_messages = self._convert_messages_to_responses_format(messages)

        # 构建请求参数
        request_params = {
            "model": self.model,
            "input": responses_messages,
            "max_output_tokens": self.max_tokens,
        }

        # 添加工具配置
        if self.tools:
            request_params["tools"] = self.tools
            if self.tool_choice:
                request_params["tool_choice"] = self.tool_choice

        # 设置推理参数
        # 注意：某些模型不支持 reasoning.effort 或 temperature
        MODELS_NO_CUSTOM_TEMP = ["gpt-5-mini", "gpt-5-nano", "o1", "o1-mini", "o1-preview"]
        MODELS_NO_REASONING = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5"]
        model_lower = self.model.lower()
        use_default_temp = any(m in model_lower for m in MODELS_NO_CUSTOM_TEMP)
        no_reasoning = any(m in model_lower for m in MODELS_NO_REASONING)

        if self.reasoning_effort != "none" and not no_reasoning:
            request_params["reasoning"] = {"effort": self.reasoning_effort}
        elif not use_default_temp:
            # 不支持 reasoning 或 reasoning=none 时，使用 temperature
            if self.temperature is not None:
                request_params["temperature"] = self.temperature

        # 传递上一次的 response_id 以保持上下文连续性
        if self._previous_response_id:
            request_params["previous_response_id"] = self._previous_response_id

        # 检查是否是 DeepSeek 或其他不支持 Responses API 的服务
        is_deepseek = self.base_url and "deepseek" in self.base_url.lower()

        if is_deepseek:
            # DeepSeek 只支持 Chat Completions API，直接使用
            logger.debug("检测到 DeepSeek API，直接使用 Chat Completions")
            return self._fallback_to_chat_completions(messages, stop, **kwargs)

        try:
            # 调用 Responses API (仅 OpenAI 官方支持)
            response = self._client.responses.create(**request_params)

            # 保存 response_id 供下次调用
            if hasattr(response, 'id'):
                self._previous_response_id = response.id

            # 解析响应内容和工具调用
            output_text = ""
            tool_calls = []

            if hasattr(response, 'output'):
                for item in response.output:
                    if hasattr(item, 'type'):
                        if item.type == "message" and hasattr(item, 'content'):
                            for content_item in item.content:
                                if hasattr(content_item, 'text'):
                                    output_text += content_item.text
                        elif item.type == "function_call":
                            # 提取工具调用
                            tool_call = {
                                "id": item.call_id if hasattr(item, 'call_id') else "",
                                "name": item.name if hasattr(item, 'name') else "",
                                "args": json.loads(item.arguments) if hasattr(item, 'arguments') else {}
                            }
                            tool_calls.append(tool_call)

            # 如果没有从 output 获取到文本，尝试 output_text
            if not output_text and hasattr(response, 'output_text'):
                output_text = response.output_text

            # 构建 LangChain 格式的响应
            if tool_calls:
                ai_message = AIMessage(
                    content=output_text,
                    tool_calls=tool_calls
                )
            else:
                ai_message = AIMessage(content=output_text)

            generation = ChatGeneration(message=ai_message)
            return ChatResult(generations=[generation])

        except Exception as e:
            # 如果 Responses API 失败，回退到 Chat Completions API
            logger.warning(f"Responses API 调用失败: {e}")
            logger.info("尝试回退到 Chat Completions API...")
            try:
                return self._fallback_to_chat_completions(messages, stop, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Chat Completions API 回退也失败: {fallback_error}")
                raise RuntimeError(f"所有 LLM 调用方式都已失败: {fallback_error}") from e

    def _fallback_to_chat_completions(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """回退到 Chat Completions API"""
        chat_messages = []
        for message in messages:
            if isinstance(message, SystemMessage):
                chat_messages.append({"role": "system", "content": message.content})
            elif isinstance(message, HumanMessage):
                chat_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, ToolMessage):
                chat_messages.append({
                    "role": "tool",
                    "tool_call_id": message.tool_call_id,
                    "content": message.content if isinstance(message.content, str) else json.dumps(message.content)
                })
            elif isinstance(message, AIMessage):
                msg = {"role": "assistant", "content": message.content or ""}
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    msg["tool_calls"] = [
                        {
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("args", {})) if isinstance(tc.get("args"), dict) else tc.get("args", "{}")
                            }
                        }
                        for tc in message.tool_calls
                    ]
                chat_messages.append(msg)
            else:
                chat_messages.append({
                    "role": "user",
                    "content": message.content if isinstance(message.content, str) else str(message.content)
                })

        # 构建请求参数
        # 注意：某些模型（如 gpt-5-mini, gpt-5-nano）不支持自定义 temperature
        MODELS_NO_CUSTOM_TEMP = ["gpt-5-mini", "gpt-5-nano", "o1", "o1-mini", "o1-preview"]
        model_lower = self.model.lower()
        use_default_temp = any(m in model_lower for m in MODELS_NO_CUSTOM_TEMP)

        request_params = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": self.max_tokens,  # 使用 max_tokens (DeepSeek 兼容)
        }

        # 只有支持的模型才添加 temperature 参数
        if not use_default_temp:
            request_params["temperature"] = self.temperature if self.temperature else 0.1

        # 添加工具 (需要转换为 Chat Completions 格式)
        if self.tools:
            # Responses API 格式: {"type": "function", "name": ..., ...}
            # Chat Completions 格式: {"type": "function", "function": {"name": ..., ...}}
            chat_tools = []
            for tool in self.tools:
                chat_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                }
                chat_tools.append(chat_tool)
            request_params["tools"] = chat_tools
            if self.tool_choice:
                request_params["tool_choice"] = self.tool_choice

        response = self._client.chat.completions.create(**request_params)

        msg = response.choices[0].message
        output_text = msg.content or ""
        tool_calls = []

        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": json.loads(tc.function.arguments) if tc.function.arguments else {}
                })

        if tool_calls:
            ai_message = AIMessage(content=output_text, tool_calls=tool_calls)
        else:
            ai_message = AIMessage(content=output_text)

        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])

    def reset_conversation(self):
        """重置对话状态，清除 previous_response_id"""
        self._previous_response_id = None

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """返回标识参数"""
        return {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "max_tokens": self.max_tokens,
        }
