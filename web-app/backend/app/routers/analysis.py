"""
分析路由

提供全面分析 API 端点（包装 TradingAgentsGraph）。
"""
import re
import os
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.routers.auth import verify_token
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)
router = APIRouter()


def validate_ticker(ticker: str) -> tuple[bool, str, str]:
    """
    验证股票代码是否有效

    Args:
        ticker: 股票代码（如 600036 或 600036.SH）

    Returns:
        (is_valid, normalized_ticker, stock_name)
    """
    # 去除空格
    ticker = ticker.strip()

    # 提取纯数字代码
    code = ticker.split('.')[0]

    # 基本格式验证：必须是6位数字
    if not re.match(r'^\d{6}$', code):
        return False, ticker, ""

    # 确定市场后缀
    if code.startswith('6'):
        full_ticker = f"{code}.SH"
    else:
        full_ticker = f"{code}.SZ"

    # 调用 Tushare 验证股票是否存在
    try:
        import tushare as ts

        token = os.environ.get("TUSHARE_TOKEN")
        if not token:
            # 没有 token，跳过验证
            logger.warning("TUSHARE_TOKEN 未设置，跳过股票代码验证")
            return True, full_ticker, ""

        pro = ts.pro_api(token)
        df = pro.stock_basic(ts_code=full_ticker, fields='ts_code,name,list_status')

        if df.empty:
            return False, full_ticker, ""

        # 检查是否已退市
        row = df.iloc[0]
        if row.get('list_status') == 'D':
            return False, full_ticker, f"{row.get('name', '')}（已退市）"

        return True, full_ticker, row.get('name', '')

    except Exception as e:
        logger.error(f"验证股票代码时出错: {e}")
        # 出错时跳过验证，让分析继续
        return True, full_ticker, ""

# 服务实例（单例）
_analysis_service: Optional[AnalysisService] = None


def get_analysis_service() -> AnalysisService:
    """获取分析服务实例"""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service


# ============== 请求/响应模型 ==============

class AnalysisRequest(BaseModel):
    """分析请求"""
    ticker: str = Field(..., description="股票代码，如 600036")
    ticker_name: Optional[str] = Field(None, description="股票名称")
    date: Optional[str] = Field(None, description="分析日期，格式 YYYY-MM-DD")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "600036",
                "ticker_name": "招商银行",
                "date": "2026-01-13"
            }
        }


class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool
    task_id: Optional[str] = None
    message: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    ticker: str
    ticker_name: str
    date: str
    status: str
    progress: dict
    logs: list
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class TaskResultResponse(BaseModel):
    """任务结果响应"""
    task_id: str
    ticker: str
    signal: str
    decision: str
    summary: Optional[dict] = None
    reports: dict


# ============== API 端点 ==============

@router.post("/run", response_model=AnalysisResponse)
async def start_analysis(
    request: AnalysisRequest,
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    启动全面分析任务

    - 调用 TradingAgentsGraph 进行完整分析
    - 分析过程约 5-10 分钟
    - 返回 task_id 用于查询进度
    """
    try:
        # 验证股票代码
        is_valid, ticker, stock_name = validate_ticker(request.ticker)

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"无效的股票代码: {request.ticker}。请输入有效的6位A股代码（如 600036、000001）"
            )

        # 使用验证返回的股票名称（如果用户没有提供）
        ticker_name = request.ticker_name or stock_name or ticker

        # 启动分析
        task_id = service.start_analysis(
            user_id=current_user["user_id"],
            ticker=ticker,
            ticker_name=ticker_name,
            date=request.date
        )

        return AnalysisResponse(
            success=True,
            task_id=task_id,
            message=f"分析任务已启动: {ticker_name}，预计需要 5-10 分钟"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    获取分析任务状态

    - 返回当前进度、已完成步骤、实时日志
    - 用于前端轮询显示进度
    """
    status = service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatusResponse(**status)


@router.get("/result/{task_id}")
async def get_task_result(
    task_id: str,
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    获取分析结果

    - 仅当任务完成后可用
    - 返回综合报告、各分析师报告、交易建议
    """
    status = service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")

    if status["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成，当前状态: {status['status']}"
        )

    result = service.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=500, detail="结果获取失败")

    return {
        "success": True,
        "task_id": task_id,
        **result
    }


@router.get("/history")
async def get_analysis_history(
    limit: int = 10,
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    获取用户的历史分析记录

    - 返回最近 N 条分析记录
    - 包含任务状态和简要结果
    """
    history = service.get_user_history(current_user["user_id"], limit=limit)
    return {
        "success": True,
        "count": len(history),
        "history": history
    }


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    取消分析任务

    - 仅能取消尚未开始的任务
    """
    success = service.cancel_task(task_id)
    if success:
        return {"success": True, "message": "任务已取消"}
    else:
        raise HTTPException(
            status_code=400,
            detail="无法取消任务（可能已开始或已完成）"
        )


@router.get("/{task_id}/report/{report_type}")
async def get_intermediate_report(
    task_id: str,
    report_type: str,
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    获取分析过程中的中间报告

    - 可在分析进行时获取已完成的分析师报告
    - report_type: market_report, sentiment_report, news_report, fundamentals_report
    """
    # 验证 report_type
    valid_types = ["market_report", "sentiment_report", "news_report", "fundamentals_report"]
    if report_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的报告类型: {report_type}。有效类型: {', '.join(valid_types)}"
        )

    # 获取任务状态
    status = service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 获取报告内容
    content = service.get_intermediate_report(task_id, report_type)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"报告 {report_type} 尚未生成或不可用"
        )

    # 报告类型到名称的映射
    report_names = {
        "market_report": "市场分析报告",
        "sentiment_report": "情绪分析报告",
        "news_report": "新闻分析报告",
        "fundamentals_report": "基本面分析报告"
    }

    return {
        "success": True,
        "task_id": task_id,
        "report_type": report_type,
        "report_name": report_names.get(report_type, report_type),
        "content": content
    }


# ============== 历史报告浏览 API ==============

@router.get("/history/browse")
async def browse_all_stocks(
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    浏览所有有历史报告的股票

    返回股票列表，包含最新分析日期和报告数量
    """
    stocks = service.browse_all_stocks()
    return {
        "success": True,
        "count": len(stocks),
        "stocks": stocks
    }


@router.get("/history/stock/{ticker}")
async def get_stock_report_dates(
    ticker: str,
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    获取某只股票的所有分析日期

    返回日期列表，包含可用的报告类型
    """
    dates = service.get_stock_report_dates(ticker)
    return {
        "success": True,
        "ticker": ticker,
        "count": len(dates),
        "dates": dates
    }


@router.get("/history/stock/{ticker}/{date}")
async def get_historical_report(
    ticker: str,
    date: str,
    report_type: str = "final_report",
    current_user: dict = Depends(verify_token),
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    获取历史报告内容

    - ticker: 股票代码（如 600036）
    - date: 分析日期（如 2026-01-15）
    - report_type: 报告类型（final_report, market_report 等）
    """
    # 验证报告类型
    valid_types = [
        "final_report", "market_report", "sentiment_report",
        "news_report", "fundamentals_report"
    ]
    if report_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的报告类型: {report_type}。有效类型: {', '.join(valid_types)}"
        )

    result = service.get_historical_report(ticker, date, report_type)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"报告不存在: {ticker}/{date}/{report_type}"
        )

    # 报告类型到名称的映射
    report_names = {
        "final_report": "综合分析报告",
        "market_report": "市场分析报告",
        "sentiment_report": "情绪分析报告",
        "news_report": "新闻分析报告",
        "fundamentals_report": "基本面分析报告"
    }

    return {
        "success": True,
        "ticker": ticker,
        "date": date,
        "report_type": report_type,
        "report_name": report_names.get(report_type, report_type),
        "content": result.get("content"),
        "summary": result.get("summary")
    }
