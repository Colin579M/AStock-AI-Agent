"""
管理员路由

提供管理后台 API：用户管理、系统监控、内容管理。
"""
from typing import Optional, List, Literal
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from app.routers.auth import verify_token, require_admin, auth_service
from app.services.admin_service import AdminService

router = APIRouter()

# 初始化管理服务
admin_service = AdminService()

# 延迟导入的服务实例
_analysis_service = None
_chat_service = None


def get_analysis_service():
    """延迟获取分析服务"""
    global _analysis_service
    if _analysis_service is None:
        try:
            from app.routers.analysis import analysis_service
            _analysis_service = analysis_service
        except ImportError:
            pass
    return _analysis_service


def get_chat_service():
    """延迟获取聊天服务"""
    global _chat_service
    if _chat_service is None:
        try:
            from app.routers.chat import chat_service
            _chat_service = chat_service
        except ImportError:
            pass
    return _chat_service


# ==================== Pydantic Models ====================

class CreateUserRequest(BaseModel):
    """创建用户请求"""
    user_id: str
    name: str
    role: Literal["user", "admin"] = "user"
    expires_at: Optional[str] = None


class CreateUserResponse(BaseModel):
    """创建用户响应"""
    success: bool
    user_id: str = ""
    access_code: str = ""  # 仅在创建时返回一次
    message: str = ""


class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    name: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    name: str
    role: str
    expires_at: Optional[str]
    is_active: bool
    created_at: Optional[str]
    created_by: Optional[str]
    last_login: Optional[str]
    login_count: int


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    backend_status: str
    chatbot_status: str
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float
    active_tasks: int
    uptime_seconds: float


class ApiStatsResponse(BaseModel):
    """API 统计响应"""
    date: str
    total_requests: int
    by_endpoint: dict
    by_user: dict
    errors: dict


class ReportInfo(BaseModel):
    """报告信息"""
    ticker: str
    date: str
    report_count: int
    summary: str
    path: str


class ConversationInfo(BaseModel):
    """对话信息"""
    user_id: str
    conversation_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class AdminLogInfo(BaseModel):
    """管理日志信息"""
    id: str
    timestamp: str
    admin_id: str
    action: str
    target_user_id: Optional[str]
    details: dict
    ip_address: str


# ==================== 用户管理 ====================

@router.get("/users", response_model=List[UserInfo])
async def list_users(admin: dict = Depends(require_admin)):
    """获取所有用户列表"""
    users = auth_service.list_users()
    return [UserInfo(**u) for u in users]


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    request: CreateUserRequest,
    req: Request,
    admin: dict = Depends(require_admin)
):
    """创建新用户"""
    success, access_code, message = auth_service.create_user(
        user_id=request.user_id,
        name=request.name,
        role=request.role,
        expires_at=request.expires_at,
        created_by=admin["user_id"]
    )

    if success:
        # 记录操作日志
        admin_service.log_admin_action(
            admin_id=admin["user_id"],
            action="user_created",
            target_user_id=request.user_id,
            details={"name": request.name, "role": request.role},
            ip_address=req.client.host if req.client else ""
        )

    return CreateUserResponse(
        success=success,
        user_id=request.user_id if success else "",
        access_code=access_code,
        message=message
    )


@router.get("/users/{user_id}", response_model=UserInfo)
async def get_user(user_id: str, admin: dict = Depends(require_admin)):
    """获取用户详情"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserInfo(**user)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    req: Request,
    admin: dict = Depends(require_admin)
):
    """更新用户信息"""
    success = auth_service.update_user(
        user_id=user_id,
        name=request.name,
        expires_at=request.expires_at,
        is_active=request.is_active
    )

    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 记录操作日志
    admin_service.log_admin_action(
        admin_id=admin["user_id"],
        action="user_updated",
        target_user_id=user_id,
        details=request.model_dump(exclude_none=True),
        ip_address=req.client.host if req.client else ""
    )

    return {"success": True}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    req: Request,
    admin: dict = Depends(require_admin)
):
    """删除用户"""
    # 不能删除自己
    if user_id == admin["user_id"]:
        raise HTTPException(status_code=400, detail="不能删除自己")

    success = auth_service.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=400, detail="无法删除用户（可能是唯一的管理员）")

    # 记录操作日志
    admin_service.log_admin_action(
        admin_id=admin["user_id"],
        action="user_deleted",
        target_user_id=user_id,
        ip_address=req.client.host if req.client else ""
    )

    return {"success": True}


@router.post("/users/{user_id}/reset-code")
async def reset_user_code(
    user_id: str,
    req: Request,
    admin: dict = Depends(require_admin)
):
    """重置用户访问码"""
    success, result = auth_service.reset_access_code(user_id)

    if not success:
        raise HTTPException(status_code=404, detail=result)

    # 记录操作日志
    admin_service.log_admin_action(
        admin_id=admin["user_id"],
        action="code_reset",
        target_user_id=user_id,
        ip_address=req.client.host if req.client else ""
    )

    return {"success": True, "access_code": result}


# ==================== 系统监控 ====================

@router.get("/stats/system", response_model=SystemStatusResponse)
async def get_system_status(admin: dict = Depends(require_admin)):
    """获取系统状态"""
    status = admin_service.get_system_status(
        analysis_service=get_analysis_service(),
        chat_service=get_chat_service()
    )
    return SystemStatusResponse(**asdict(status))


@router.get("/stats/api", response_model=ApiStatsResponse)
async def get_api_stats(
    date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """获取 API 统计"""
    stats = admin_service.get_api_stats(date)
    return ApiStatsResponse(**asdict(stats))


# ==================== 内容管理 ====================

@router.get("/content/reports", response_model=List[ReportInfo])
async def list_reports(admin: dict = Depends(require_admin)):
    """获取所有分析报告"""
    reports = admin_service.list_all_reports()
    return [ReportInfo(**r) for r in reports]


@router.delete("/content/reports/{ticker}/{date}")
async def delete_report(
    ticker: str,
    date: str,
    req: Request,
    admin: dict = Depends(require_admin)
):
    """删除分析报告"""
    success = admin_service.delete_report(ticker, date)

    if not success:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 记录操作日志
    admin_service.log_admin_action(
        admin_id=admin["user_id"],
        action="report_deleted",
        details={"ticker": ticker, "date": date},
        ip_address=req.client.host if req.client else ""
    )

    return {"success": True}


@router.get("/content/conversations", response_model=List[ConversationInfo])
async def list_conversations(admin: dict = Depends(require_admin)):
    """获取所有对话记录"""
    conversations = admin_service.list_all_conversations(
        chat_service=get_chat_service()
    )
    return [ConversationInfo(**c) for c in conversations]


@router.delete("/content/conversations/{user_id}/{conversation_id}")
async def delete_conversation(
    user_id: str,
    conversation_id: str,
    req: Request,
    admin: dict = Depends(require_admin)
):
    """删除对话"""
    success = admin_service.delete_conversation(
        user_id=user_id,
        conversation_id=conversation_id,
        chat_service=get_chat_service()
    )

    if not success:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 记录操作日志
    admin_service.log_admin_action(
        admin_id=admin["user_id"],
        action="conversation_deleted",
        target_user_id=user_id,
        details={"conversation_id": conversation_id},
        ip_address=req.client.host if req.client else ""
    )

    return {"success": True}


# ==================== 操作日志 ====================

@router.get("/logs", response_model=List[AdminLogInfo])
async def get_admin_logs(
    limit: int = 100,
    action: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """获取管理员操作日志"""
    logs = admin_service.get_admin_logs(limit=limit, action=action)
    return [AdminLogInfo(**log) for log in logs]


@router.get("/logs/errors")
async def get_error_logs(
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """获取错误日志"""
    return admin_service.get_error_logs(limit=limit)
