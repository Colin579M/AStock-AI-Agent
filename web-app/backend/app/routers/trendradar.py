# coding=utf-8
"""
TrendRadar 热点监控路由

提供热榜数据、RSS 订阅、关键词筛选和 AI 分析功能。
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.routers.auth import verify_token
from app.services.trendradar_service import get_trendradar_service


router = APIRouter()


# ==================== 请求/响应模型 ====================

class KeywordsRequest(BaseModel):
    """关键词配置请求"""
    keywords: List[str]


class FilterRequest(BaseModel):
    """筛选请求"""
    platform_ids: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class AnalyzeRequest(BaseModel):
    """AI 分析请求"""
    platform_ids: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    include_rss: bool = False
    max_news: int = 50


class RSSFeedRequest(BaseModel):
    """添加 RSS 源请求"""
    feed_id: str
    name: str
    url: str
    max_age_days: int = 3


# ==================== 平台相关 ====================

@router.get("/platforms")
async def get_platforms(payload: dict = Depends(verify_token)):
    """获取支持的平台列表"""
    service = get_trendradar_service()
    platforms = await service.get_platforms()
    return {
        "success": True,
        "platforms": platforms,
    }


# ==================== 热榜相关 ====================

@router.get("/hotlist")
async def get_hotlist(
    platforms: Optional[str] = Query(None, description="平台ID列表，逗号分隔"),
    refresh: bool = Query(False, description="强制刷新缓存"),
    payload: dict = Depends(verify_token),
):
    """
    获取热榜数据

    支持多个平台，用逗号分隔：?platforms=weibo,zhihu,baidu
    """
    service = get_trendradar_service()

    platform_ids = None
    if platforms:
        platform_ids = [p.strip() for p in platforms.split(",") if p.strip()]

    data = await service.get_hotlist(
        platform_ids=platform_ids,
        use_cache=not refresh,
    )

    return data


@router.get("/hotlist/{platform_id}")
async def get_single_hotlist(
    platform_id: str,
    refresh: bool = Query(False, description="强制刷新缓存"),
    payload: dict = Depends(verify_token),
):
    """获取单个平台热榜"""
    service = get_trendradar_service()

    # 验证平台 ID
    platforms = await service.get_platforms()
    valid_ids = [p["id"] for p in platforms]

    if platform_id not in valid_ids:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform_id}")

    data = await service.get_single_hotlist(
        platform_id=platform_id,
        use_cache=not refresh,
    )

    return data


# ==================== 关键词筛选 ====================

@router.get("/keywords")
async def get_keywords(payload: dict = Depends(verify_token)):
    """获取用户关键词配置"""
    service = get_trendradar_service()
    user_id = payload.get("user_id", "")
    keywords = service.get_user_keywords(user_id)
    return {
        "success": True,
        "keywords": keywords,
    }


@router.post("/keywords")
async def set_keywords(
    request: KeywordsRequest,
    payload: dict = Depends(verify_token),
):
    """设置用户关键词配置"""
    service = get_trendradar_service()
    user_id = payload.get("user_id", "")
    service.set_user_keywords(user_id, request.keywords)
    return {
        "success": True,
        "keywords": service.get_user_keywords(user_id),
    }


@router.post("/filter")
async def filter_hotlist(
    request: FilterRequest,
    payload: dict = Depends(verify_token),
):
    """按关键词筛选热榜"""
    service = get_trendradar_service()
    user_id = payload.get("user_id", "")

    data = await service.filter_hotlist(
        platform_ids=request.platform_ids,
        keywords=request.keywords,
        user_id=user_id,
    )

    return data


# ==================== RSS 订阅 ====================

@router.get("/rss/feeds")
async def get_rss_feeds(payload: dict = Depends(verify_token)):
    """获取 RSS 源列表"""
    service = get_trendradar_service()
    user_id = payload.get("user_id", "")
    feeds = service.get_rss_feeds(user_id)
    return {
        "success": True,
        "feeds": feeds,
    }


@router.get("/rss/items")
async def get_rss_items(
    feeds: Optional[str] = Query(None, description="RSS源ID列表，逗号分隔"),
    payload: dict = Depends(verify_token),
):
    """获取 RSS 内容"""
    service = get_trendradar_service()
    user_id = payload.get("user_id", "")

    feed_ids = None
    if feeds:
        feed_ids = [f.strip() for f in feeds.split(",") if f.strip()]

    data = await service.get_rss_items(user_id, feed_ids)
    return data


@router.post("/rss/subscribe")
async def add_rss_feed(
    request: RSSFeedRequest,
    payload: dict = Depends(verify_token),
):
    """添加 RSS 订阅源"""
    service = get_trendradar_service()
    user_id = payload.get("user_id", "")

    result = service.add_rss_feed(
        user_id=user_id,
        feed_id=request.feed_id,
        name=request.name,
        url=request.url,
        max_age_days=request.max_age_days,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.delete("/rss/unsubscribe/{feed_id}")
async def remove_rss_feed(
    feed_id: str,
    payload: dict = Depends(verify_token),
):
    """删除 RSS 订阅源"""
    service = get_trendradar_service()
    user_id = payload.get("user_id", "")

    result = service.remove_rss_feed(user_id, feed_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# ==================== AI 分析 ====================

@router.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
    payload: dict = Depends(verify_token),
):
    """AI 智能分析热点"""
    service = get_trendradar_service()
    user_id = payload.get("user_id", "")

    result = await service.analyze(
        platform_ids=request.platform_ids,
        keywords=request.keywords,
        include_rss=request.include_rss,
        max_news=request.max_news,
        user_id=user_id,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "AI 分析失败"))

    return result


# ==================== 缓存管理 ====================

@router.post("/cache/clear")
async def clear_cache(payload: dict = Depends(verify_token)):
    """清空所有缓存（管理员功能）"""
    # 可以在这里添加管理员权限检查
    role = payload.get("role", "")
    if role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    service = get_trendradar_service()
    service.clear_all_cache()

    return {
        "success": True,
        "message": "缓存已清空",
    }
