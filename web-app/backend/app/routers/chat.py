"""
聊天路由

提供对话模式 API，使用 ChatbotGraph 处理用户查询。
"""
from typing import Optional, List
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.routers.auth import verify_token
from app.services.chat_service import ChatService

router = APIRouter()

# 初始化聊天服务
chat_service = ChatService()


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool
    response: Optional[str] = None
    query_type: Optional[str] = None  # quick / analysis
    conversation_id: str
    error: Optional[str] = None


class ConversationSummary(BaseModel):
    """对话摘要"""
    conversation_id: str
    title: str
    last_message: str
    updated_at: str
    message_count: int


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    payload: dict = Depends(verify_token)
):
    """
    发送消息

    - 使用 ChatbotGraph 处理查询
    - 自动路由到 QuickAgent 或 AnalysisAgent
    """
    user_id = payload["user_id"]

    try:
        result = chat_service.chat(
            user_id=user_id,
            message=request.message,
            conversation_id=request.conversation_id
        )

        return ChatResponse(
            success=True,
            response=result["response"],
            query_type=result.get("query_type"),
            conversation_id=result["conversation_id"]
        )

    except Exception as e:
        return ChatResponse(
            success=False,
            error=str(e),
            conversation_id=request.conversation_id or "error"
        )


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    payload: dict = Depends(verify_token)
):
    """
    流式发送消息，返回进度事件

    使用 Server-Sent Events (SSE) 实时推送:
    - thinking: 思考过程
    - tool: 工具调用
    - done: 最终响应
    - error: 错误信息
    """
    user_id = payload["user_id"]

    async def event_generator():
        try:
            async for event in chat_service.chat_stream(
                user_id=user_id,
                message=request.message,
                conversation_id=request.conversation_id
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        }
    )


@router.get("/conversations", response_model=List[ConversationSummary])
async def get_conversations(payload: dict = Depends(verify_token)):
    """获取对话列表"""
    user_id = payload["user_id"]
    return chat_service.get_conversations(user_id)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    payload: dict = Depends(verify_token)
):
    """获取对话详情"""
    user_id = payload["user_id"]
    conversation = chat_service.get_conversation(user_id, conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    payload: dict = Depends(verify_token)
):
    """删除对话"""
    user_id = payload["user_id"]
    success = chat_service.delete_conversation(user_id, conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="对话不存在")

    return {"success": True}
