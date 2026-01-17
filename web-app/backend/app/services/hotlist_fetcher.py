# coding=utf-8
"""
热榜数据获取器

负责从 NewsNow API 抓取热点数据，支持：
- 多平台数据获取
- 自动重试机制
- 内存缓存
"""

import json
import random
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import httpx


@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    timestamp: datetime

    def is_expired(self, ttl_seconds: int) -> bool:
        return datetime.now() - self.timestamp > timedelta(seconds=ttl_seconds)


class HotlistCache:
    """热榜数据缓存"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired(self._ttl):
                return entry.data
            else:
                del self._cache[key]
        return None

    def set(self, key: str, data: Any):
        """设置缓存数据"""
        self._cache[key] = CacheEntry(data=data, timestamp=datetime.now())

    def clear_expired(self):
        """清理过期缓存"""
        expired = [k for k, v in self._cache.items() if v.is_expired(self._ttl)]
        for k in expired:
            del self._cache[k]

    def clear_all(self):
        """清空所有缓存"""
        self._cache.clear()


class HotlistFetcher:
    """热榜数据获取器"""

    # 默认 API 地址
    DEFAULT_API_URL = "https://newsnow.busiyi.world/api/s"

    # 默认请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }

    # 支持的平台列表
    PLATFORMS = {
        "toutiao": "今日头条",
        "baidu": "百度热搜",
        "wallstreetcn-hot": "华尔街见闻",
        "thepaper": "澎湃新闻",
        "bilibili-hot-search": "B站热搜",
        "cls-hot": "财联社热门",
        "ifeng": "凤凰网",
        "tieba": "贴吧",
        "weibo": "微博",
        "douyin": "抖音",
        "zhihu": "知乎",
    }

    def __init__(
        self,
        api_url: Optional[str] = None,
        cache_ttl: int = 300,  # 5分钟缓存
    ):
        """
        初始化数据获取器

        Args:
            api_url: API 基础 URL（可选，默认使用 DEFAULT_API_URL）
            cache_ttl: 缓存有效期（秒）
        """
        self.api_url = api_url or self.DEFAULT_API_URL
        self.cache = HotlistCache(ttl_seconds=cache_ttl)

    async def fetch_platform(
        self,
        platform_id: str,
        max_retries: int = 2,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        获取单个平台热榜数据

        Args:
            platform_id: 平台 ID
            max_retries: 最大重试次数
            use_cache: 是否使用缓存

        Returns:
            平台热榜数据
        """
        # 检查缓存
        if use_cache:
            cached = self.cache.get(f"hotlist:{platform_id}")
            if cached:
                return cached

        url = f"{self.api_url}?id={platform_id}&latest"

        retries = 0
        last_error = None

        async with httpx.AsyncClient(timeout=10) as client:
            while retries <= max_retries:
                try:
                    response = await client.get(url, headers=self.DEFAULT_HEADERS)
                    response.raise_for_status()

                    data = response.json()
                    status = data.get("status", "unknown")

                    if status not in ["success", "cache"]:
                        raise ValueError(f"响应状态异常: {status}")

                    # 处理数据
                    result = self._process_response(platform_id, data)

                    # 存入缓存
                    if use_cache:
                        self.cache.set(f"hotlist:{platform_id}", result)

                    return result

                except Exception as e:
                    last_error = e
                    retries += 1
                    if retries <= max_retries:
                        wait_time = random.uniform(1, 3) + (retries - 1)
                        await asyncio.sleep(wait_time)

        # 所有重试失败
        return {
            "platform_id": platform_id,
            "platform_name": self.PLATFORMS.get(platform_id, platform_id),
            "success": False,
            "error": str(last_error),
            "items": [],
            "timestamp": datetime.now().isoformat(),
        }

    def _process_response(self, platform_id: str, data: Dict) -> Dict[str, Any]:
        """处理 API 响应数据"""
        items = []

        for index, item in enumerate(data.get("items", []), 1):
            title = item.get("title")
            # 跳过无效标题
            if title is None or isinstance(title, float) or not str(title).strip():
                continue

            items.append({
                "rank": index,
                "title": str(title).strip(),
                "url": item.get("url", ""),
                "mobile_url": item.get("mobileUrl", ""),
                "hot": item.get("hot", ""),  # 热度值（部分平台有）
            })

        return {
            "platform_id": platform_id,
            "platform_name": self.PLATFORMS.get(platform_id, platform_id),
            "success": True,
            "error": None,
            "items": items,
            "count": len(items),
            "timestamp": datetime.now().isoformat(),
            "cached": data.get("status") == "cache",
        }

    async def fetch_multiple(
        self,
        platform_ids: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        获取多个平台热榜数据

        Args:
            platform_ids: 平台 ID 列表（None 表示全部）
            use_cache: 是否使用缓存

        Returns:
            所有平台的热榜数据
        """
        if platform_ids is None:
            platform_ids = list(self.PLATFORMS.keys())

        # 验证平台 ID
        valid_ids = [pid for pid in platform_ids if pid in self.PLATFORMS]

        # 并发获取所有平台数据
        tasks = [self.fetch_platform(pid, use_cache=use_cache) for pid in valid_ids]
        results = await asyncio.gather(*tasks)

        # 组织返回数据
        platforms_data = {}
        success_count = 0
        fail_count = 0

        for result in results:
            pid = result["platform_id"]
            platforms_data[pid] = result
            if result["success"]:
                success_count += 1
            else:
                fail_count += 1

        return {
            "success": True,
            "platforms": platforms_data,
            "summary": {
                "total": len(valid_ids),
                "success": success_count,
                "failed": fail_count,
            },
            "timestamp": datetime.now().isoformat(),
        }

    def get_platforms_list(self) -> List[Dict[str, str]]:
        """获取支持的平台列表"""
        return [
            {"id": pid, "name": name}
            for pid, name in self.PLATFORMS.items()
        ]

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear_all()


# 单例实例
_fetcher_instance: Optional[HotlistFetcher] = None


def get_hotlist_fetcher() -> HotlistFetcher:
    """获取热榜获取器单例"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = HotlistFetcher()
    return _fetcher_instance
