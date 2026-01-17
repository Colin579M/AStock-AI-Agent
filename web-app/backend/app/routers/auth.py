"""
认证路由

提供 Access Code 验证和 JWT token 管理。
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

from app.services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer()

# JWT 配置 - 必须通过环境变量设置，不使用不安全的默认值
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError(
        "JWT_SECRET 环境变量未设置！请在 .env 文件中设置一个安全的密钥。"
        "可使用以下命令生成: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 7 天


class LoginRequest(BaseModel):
    """登录请求"""
    access_code: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    is_first_login: bool = False
    message: Optional[str] = None


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    name: str
    role: str = "user"
    expires_at: Optional[str] = None


def create_token(user_id: str, name: str, role: str = "user") -> str:
    """创建 JWT token"""
    payload = {
        "user_id": user_id,
        "name": name,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """验证 JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token")


def require_admin(current_user: dict = Depends(verify_token)) -> dict:
    """验证管理员权限"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# 初始化认证服务
auth_service = AuthService()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    登录验证

    - 验证 Access Code
    - 返回 JWT token
    """
    result = auth_service.verify_access_code(request.access_code)

    if not result["success"]:
        return LoginResponse(
            success=False,
            message=result.get("message", "验证失败")
        )

    user = result["user"]
    token = create_token(user["user_id"], user["name"], user.get("role", "user"))

    # 记录登录
    is_first = auth_service.record_login(user["user_id"])

    return LoginResponse(
        success=True,
        token=token,
        user={
            "user_id": user["user_id"],
            "name": user["name"],
            "role": user.get("role", "user")
        },
        is_first_login=is_first
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(payload: dict = Depends(verify_token)):
    """获取当前用户信息"""
    return UserInfo(
        user_id=payload["user_id"],
        name=payload["name"],
        role=payload.get("role", "user")
    )


@router.post("/logout")
async def logout(payload: dict = Depends(verify_token)):
    """登出（客户端删除 token 即可）"""
    return {"success": True, "message": "已登出"}
