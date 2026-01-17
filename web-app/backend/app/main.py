"""
TradingAgents Web Backend - FastAPI 主入口

提供 REST API 服务：
- /api/auth - 认证服务
- /api/chat - 对话模式 (ChatbotGraph)
- /api/analysis - 全面分析模式 (TradingAgentsGraph)
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量（在其他导入之前）
from dotenv import load_dotenv
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
    sys.stderr.write(f"[main.py] 已加载环境变量: {env_file}\n")
    sys.stderr.flush()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, chat, analysis, admin, trendradar


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("TradingAgents Web Backend 启动中...")
    yield
    # 关闭时
    print("TradingAgents Web Backend 关闭中...")


app = FastAPI(
    title="TradingAgents API",
    description="股票分析助手 API 服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/chat", tags=["对话"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["分析"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理"])
app.include_router(trendradar.router, prefix="/api/trendradar", tags=["热点监控"])


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "TradingAgents API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "chat": "/api/chat",
            "analysis": "/api/analysis",
            "admin": "/api/admin",
            "trendradar": "/api/trendradar"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
