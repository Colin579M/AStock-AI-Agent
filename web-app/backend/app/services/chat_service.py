"""
聊天服务

封装 ChatbotGraph，提供对话管理功能。
"""
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """聊天服务"""

    def __init__(self):
        """初始化聊天服务"""
        self._chatbot = None  # 延迟加载
        self._conversations: Dict[str, Dict] = {}  # user_id -> {conv_id -> conversation}

    @property
    def chatbot(self):
        """延迟加载 ChatbotGraph"""
        if self._chatbot is None:
            try:
                logger.info("🚀 开始初始化 ChatbotGraph...")
                import time
                start = time.time()
                from tradingagents.chatbot import ChatbotGraph
                self._chatbot = ChatbotGraph()
                elapsed = time.time() - start
                logger.info(f"✅ ChatbotGraph 初始化成功，耗时 {elapsed:.2f}s")
            except Exception as e:
                logger.error(f"❌ ChatbotGraph 初始化失败: {e}", exc_info=True)
                raise RuntimeError(f"无法初始化 Chatbot: {e}")
        return self._chatbot

    def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> dict:
        """
        处理聊天消息

        Args:
            user_id: 用户 ID
            message: 用户消息
            conversation_id: 对话 ID（可选，新对话则创建）

        Returns:
            dict: {
                "response": str,
                "query_type": str,
                "conversation_id": str
            }
        """
        # 获取或创建对话
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())[:8]

        if user_id not in self._conversations:
            self._conversations[user_id] = {}

        if conversation_id not in self._conversations[user_id]:
            self._conversations[user_id][conversation_id] = {
                "id": conversation_id,
                "title": message[:20] + "..." if len(message) > 20 else message,
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

        conversation = self._conversations[user_id][conversation_id]

        # 添加用户消息
        conversation["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # 调用 ChatbotGraph
        try:
            response = self.chatbot.chat(message)
            query_type = self._get_query_type(message)
        except Exception as e:
            logger.error(f"Chatbot 调用失败: {e}")
            response = f"抱歉，处理请求时发生错误: {str(e)}"
            query_type = "error"

        # 添加助手消息
        conversation["messages"].append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        # 更新对话时间
        conversation["updated_at"] = datetime.now().isoformat()

        return {
            "response": response,
            "query_type": query_type,
            "conversation_id": conversation_id
        }

    async def chat_stream(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[dict, None]:
        """
        流式处理聊天消息，返回进度事件

        Args:
            user_id: 用户 ID
            message: 用户消息
            conversation_id: 对话 ID

        Yields:
            dict: 进度事件 {"type": str, "content": str}
        """
        # 获取或创建对话
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())[:8]

        if user_id not in self._conversations:
            self._conversations[user_id] = {}

        if conversation_id not in self._conversations[user_id]:
            self._conversations[user_id][conversation_id] = {
                "id": conversation_id,
                "title": message[:20] + "..." if len(message) > 20 else message,
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

        conversation = self._conversations[user_id][conversation_id]

        # 添加用户消息
        conversation["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # 初始 thinking 事件
        logger.info(f"🌊 开始流式响应，消息: {message[:30]}...")
        yield {"type": "thinking", "content": f"分析问题: {message[:30]}..."}

        # 在线程中运行同步的 chatbot（因为 LangGraph 是同步的）
        progress_queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def progress_callback(event_type: str, content: str):
            """进度回调，将事件放入队列"""
            try:
                loop.call_soon_threadsafe(
                    progress_queue.put_nowait,
                    {"type": event_type, "content": content}
                )
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

        def run_chatbot():
            """在线程中运行 chatbot"""
            import time
            try:
                logger.info(f"📝 开始处理消息: {message[:50]}...")
                start = time.time()
                result = self.chatbot.chat_with_progress(
                    message,
                    progress_callback=progress_callback
                )
                elapsed = time.time() - start
                logger.info(f"✅ 消息处理完成，耗时 {elapsed:.2f}s，回复长度: {len(result) if result else 0}")
                return result
            except Exception as e:
                logger.error(f"❌ Chatbot 执行失败: {e}", exc_info=True)
                raise

        # 使用线程池执行
        logger.info(f"🔄 启动线程池处理消息...")
        executor = ThreadPoolExecutor(max_workers=1)
        future = loop.run_in_executor(executor, run_chatbot)

        # 持续读取进度事件
        try:
            while not future.done():
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    yield event
                except asyncio.TimeoutError:
                    continue

            # 获取最终结果
            response = await asyncio.wrap_future(future)

            # 读取队列中剩余的事件（future 完成后可能还有事件）
            while not progress_queue.empty():
                try:
                    event = progress_queue.get_nowait()
                    yield event
                except Exception:
                    break

            # 添加助手消息
            conversation["messages"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            conversation["updated_at"] = datetime.now().isoformat()

            # 发送完成事件
            logger.info(f"🎉 发送 done 事件，回复长度: {len(response) if response else 0}")
            yield {
                "type": "done",
                "content": response,
                "conversation_id": conversation_id
            }

        except Exception as e:
            logger.error(f"❌ 流式聊天失败: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}

        finally:
            executor.shutdown(wait=False)

    def _get_query_type(self, message: str) -> str:
        """获取查询类型"""
        try:
            from tradingagents.chatbot.agents.router import get_router
            router = get_router()
            query_type = router.route(message)
            return query_type.value
        except Exception:
            return "unknown"

    def get_conversations(self, user_id: str) -> List[dict]:
        """获取用户的所有对话"""
        if user_id not in self._conversations:
            return []

        conversations = []
        for conv_id, conv in self._conversations[user_id].items():
            last_message = ""
            if conv["messages"]:
                last_msg = conv["messages"][-1]
                last_message = last_msg["content"][:50] + "..." if len(last_msg["content"]) > 50 else last_msg["content"]

            conversations.append({
                "conversation_id": conv_id,
                "title": conv["title"],
                "last_message": last_message,
                "updated_at": conv["updated_at"],
                "message_count": len(conv["messages"])
            })

        # 按更新时间排序
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        return conversations

    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[dict]:
        """获取特定对话"""
        if user_id not in self._conversations:
            return None
        return self._conversations[user_id].get(conversation_id)

    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """删除对话"""
        if user_id not in self._conversations:
            return False
        if conversation_id not in self._conversations[user_id]:
            return False

        del self._conversations[user_id][conversation_id]
        return True
