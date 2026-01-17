# coding=utf-8
"""
TrendRadar 热点监控服务

核心服务类，协调：
- 热榜数据获取
- RSS 订阅管理
- 关键词筛选
- AI 分析
"""

import os
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from .hotlist_fetcher import get_hotlist_fetcher, HotlistFetcher, HotlistCache


@dataclass
class RSSFeed:
    """RSS 订阅源"""
    id: str
    name: str
    url: str
    enabled: bool = True
    max_age_days: int = 3


class TrendRadarService:
    """TrendRadar 热点监控服务"""

    def __init__(self):
        self.hotlist_fetcher = get_hotlist_fetcher()

        # RSS 缓存（15分钟）
        self.rss_cache = HotlistCache(ttl_seconds=900)

        # AI 分析结果缓存（30分钟）
        self.ai_cache = HotlistCache(ttl_seconds=1800)

        # 用户关键词配置
        self._user_keywords: Dict[str, List[str]] = {}

        # 默认 RSS 源
        self._default_rss_feeds = [
            RSSFeed(id="hacker-news", name="Hacker News", url="https://hnrss.org/frontpage"),
            RSSFeed(id="ruanyifeng", name="阮一峰的网络日志", url="http://www.ruanyifeng.com/blog/atom.xml", max_age_days=7),
        ]

        # 用户自定义 RSS 源
        self._user_rss_feeds: Dict[str, List[RSSFeed]] = {}

    # ==================== 热榜相关 ====================

    async def get_platforms(self) -> List[Dict[str, str]]:
        """获取支持的平台列表"""
        return self.hotlist_fetcher.get_platforms_list()

    async def get_hotlist(
        self,
        platform_ids: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """获取热榜数据"""
        return await self.hotlist_fetcher.fetch_multiple(
            platform_ids=platform_ids,
            use_cache=use_cache,
        )

    async def get_single_hotlist(
        self,
        platform_id: str,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """获取单个平台热榜"""
        return await self.hotlist_fetcher.fetch_platform(
            platform_id=platform_id,
            use_cache=use_cache,
        )

    # ==================== 关键词筛选 ====================

    def get_user_keywords(self, user_id: str) -> List[str]:
        """获取用户关键词配置"""
        return self._user_keywords.get(user_id, [])

    def set_user_keywords(self, user_id: str, keywords: List[str]) -> bool:
        """设置用户关键词配置"""
        # 清理空白和重复
        cleaned = list(set(k.strip() for k in keywords if k.strip()))
        self._user_keywords[user_id] = cleaned
        return True

    def filter_by_keywords(
        self,
        items: List[Dict],
        keywords: List[str],
    ) -> List[Dict]:
        """
        按关键词筛选热点

        支持的语法：
        - 普通关键词：华为
        - 排除词：!广告
        - 必须词：+发布会
        - 正则：/华为|鸿蒙/
        """
        if not keywords:
            return items

        # 分类关键词
        include_words = []
        exclude_words = []
        require_words = []
        regex_patterns = []

        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            if kw.startswith("!"):
                exclude_words.append(kw[1:])
            elif kw.startswith("+"):
                require_words.append(kw[1:])
            elif kw.startswith("/") and kw.endswith("/"):
                try:
                    regex_patterns.append(re.compile(kw[1:-1], re.IGNORECASE))
                except re.error:
                    pass  # 忽略无效正则
            else:
                include_words.append(kw)

        filtered = []
        for item in items:
            title = item.get("title", "")
            if not title:
                continue

            # 排除词检查
            if any(w in title for w in exclude_words):
                continue

            # 必须词检查
            if require_words and not all(w in title for w in require_words):
                continue

            # 包含词或正则匹配
            matched = False
            if include_words:
                matched = any(w in title for w in include_words)
            if not matched and regex_patterns:
                matched = any(p.search(title) for p in regex_patterns)

            # 如果没有包含词和正则，只要通过排除和必须检查即可
            if not include_words and not regex_patterns:
                matched = True

            if matched:
                filtered.append(item)

        return filtered

    async def filter_hotlist(
        self,
        platform_ids: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取并筛选热榜数据

        Args:
            platform_ids: 平台 ID 列表
            keywords: 关键词列表（优先使用）
            user_id: 用户 ID（用于获取用户配置的关键词）
        """
        # 获取热榜
        hotlist_data = await self.get_hotlist(platform_ids)

        # 确定关键词
        kw_list = keywords
        if not kw_list and user_id:
            kw_list = self.get_user_keywords(user_id)

        if not kw_list:
            return hotlist_data

        # 筛选每个平台的数据
        for pid, pdata in hotlist_data.get("platforms", {}).items():
            if pdata.get("success"):
                original_count = len(pdata.get("items", []))
                pdata["items"] = self.filter_by_keywords(pdata["items"], kw_list)
                pdata["filtered_count"] = len(pdata["items"])
                pdata["original_count"] = original_count

        hotlist_data["keywords_used"] = kw_list
        return hotlist_data

    # ==================== RSS 订阅 ====================

    def get_rss_feeds(self, user_id: str) -> List[Dict]:
        """获取 RSS 源列表"""
        user_feeds = self._user_rss_feeds.get(user_id, [])
        all_feeds = self._default_rss_feeds + user_feeds
        return [
            {
                "id": f.id,
                "name": f.name,
                "url": f.url,
                "enabled": f.enabled,
                "max_age_days": f.max_age_days,
                "is_default": f in self._default_rss_feeds,
            }
            for f in all_feeds
        ]

    def add_rss_feed(
        self,
        user_id: str,
        feed_id: str,
        name: str,
        url: str,
        max_age_days: int = 3,
    ) -> Dict[str, Any]:
        """添加 RSS 源"""
        if user_id not in self._user_rss_feeds:
            self._user_rss_feeds[user_id] = []

        # 检查重复
        for f in self._user_rss_feeds[user_id]:
            if f.id == feed_id or f.url == url:
                return {"success": False, "error": "RSS 源已存在"}

        feed = RSSFeed(id=feed_id, name=name, url=url, max_age_days=max_age_days)
        self._user_rss_feeds[user_id].append(feed)

        return {"success": True, "feed": {"id": feed.id, "name": feed.name, "url": feed.url}}

    def remove_rss_feed(self, user_id: str, feed_id: str) -> Dict[str, Any]:
        """删除 RSS 源"""
        if user_id not in self._user_rss_feeds:
            return {"success": False, "error": "未找到用户 RSS 配置"}

        feeds = self._user_rss_feeds[user_id]
        for i, f in enumerate(feeds):
            if f.id == feed_id:
                del feeds[i]
                return {"success": True}

        return {"success": False, "error": "未找到该 RSS 源"}

    async def get_rss_items(
        self,
        user_id: str,
        feed_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        获取 RSS 内容

        注意: 简化实现，实际需要 feedparser 库
        """
        try:
            import feedparser
        except ImportError:
            return {
                "success": False,
                "error": "RSS 功能需要安装 feedparser: pip install feedparser",
                "items": [],
            }

        feeds = self.get_rss_feeds(user_id)
        if feed_ids:
            feeds = [f for f in feeds if f["id"] in feed_ids]

        all_items = []
        errors = []

        for feed in feeds:
            if not feed["enabled"]:
                continue

            # 检查缓存
            cache_key = f"rss:{feed['id']}"
            cached = self.rss_cache.get(cache_key)
            if cached:
                all_items.extend(cached)
                continue

            try:
                parsed = feedparser.parse(feed["url"])
                items = []

                max_age = timedelta(days=feed["max_age_days"])
                now = datetime.now()

                for entry in parsed.entries[:20]:  # 限制每源20条
                    # 解析发布时间
                    pub_date = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])

                    # 过滤过旧文章
                    if pub_date and (now - pub_date) > max_age:
                        continue

                    items.append({
                        "feed_id": feed["id"],
                        "feed_name": feed["name"],
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", "")[:200] if entry.get("summary") else "",
                        "published": pub_date.isoformat() if pub_date else None,
                    })

                # 缓存
                self.rss_cache.set(cache_key, items)
                all_items.extend(items)

            except Exception as e:
                errors.append({"feed_id": feed["id"], "error": str(e)})

        return {
            "success": True,
            "items": all_items,
            "count": len(all_items),
            "errors": errors if errors else None,
            "timestamp": datetime.now().isoformat(),
        }

    # ==================== AI 分析 ====================

    async def analyze(
        self,
        platform_ids: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        include_rss: bool = False,
        max_news: int = 50,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        AI 智能分析热点

        Args:
            platform_ids: 平台列表
            keywords: 关键词过滤
            include_rss: 是否包含 RSS
            max_news: 最大分析条数
            user_id: 用户 ID
        """
        # 检查 API Key（支持多种配置方式）
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return {
                "success": False,
                "error": "未配置 AI API Key，请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY",
            }

        # 获取热榜数据
        if keywords:
            hotlist_data = await self.filter_hotlist(platform_ids, keywords, user_id)
        else:
            hotlist_data = await self.get_hotlist(platform_ids)

        # 收集新闻
        news_items = []
        for pid, pdata in hotlist_data.get("platforms", {}).items():
            if pdata.get("success"):
                for item in pdata.get("items", []):
                    news_items.append({
                        "platform": pdata.get("platform_name", pid),
                        "title": item.get("title", ""),
                        "rank": item.get("rank", 0),
                    })

        # 包含 RSS
        rss_items = []
        if include_rss and user_id:
            rss_data = await self.get_rss_items(user_id)
            if rss_data.get("success"):
                for item in rss_data.get("items", []):
                    rss_items.append({
                        "source": item.get("feed_name", ""),
                        "title": item.get("title", ""),
                    })

        total_items = len(news_items) + len(rss_items)
        if total_items == 0:
            return {
                "success": False,
                "error": "没有可分析的新闻内容",
            }

        # 生成缓存 key
        cache_key = self._make_cache_key(news_items[:max_news], rss_items[:max_news])
        cached = self.ai_cache.get(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

        # 准备 AI 输入
        news_content = self._prepare_news_content(news_items, rss_items, max_news)

        # 调用 DeepSeek API
        try:
            result = await self._call_deepseek(api_key, news_content, len(news_items), len(rss_items))
            result["stats"] = {
                "total_news": total_items,
                "analyzed_news": min(total_items, max_news),
                "hotlist_count": len(news_items),
                "rss_count": len(rss_items),
            }

            # 缓存结果
            self.ai_cache.set(cache_key, result)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"AI 分析失败: {str(e)}",
            }

    def _make_cache_key(self, news: List, rss: List) -> str:
        """生成缓存 key"""
        content = json.dumps({"news": news, "rss": rss}, sort_keys=True, ensure_ascii=False)
        return f"ai:{hashlib.md5(content.encode()).hexdigest()}"

    def _prepare_news_content(
        self,
        news_items: List[Dict],
        rss_items: List[Dict],
        max_news: int,
    ) -> str:
        """准备新闻内容文本"""
        lines = []
        count = 0

        if news_items:
            lines.append("### 热榜新闻")
            for item in news_items:
                if count >= max_news:
                    break
                lines.append(f"- [{item['platform']}] {item['title']} (排名:{item['rank']})")
                count += 1

        if rss_items and count < max_news:
            lines.append("\n### RSS 订阅")
            for item in rss_items:
                if count >= max_news:
                    break
                lines.append(f"- [{item['source']}] {item['title']}")
                count += 1

        return "\n".join(lines)

    async def _call_deepseek(
        self,
        api_key: str,
        news_content: str,
        hotlist_count: int,
        rss_count: int,
    ) -> Dict[str, Any]:
        """调用 DeepSeek API"""
        import httpx

        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        system_prompt = """你是一位专业的新闻分析师，擅长从海量信息中提取关键洞察。
请分析以下热点新闻，提供深度分析报告。"""

        user_prompt = f"""## 分析任务

请分析以下 {hotlist_count} 条热榜新闻和 {rss_count} 条 RSS 订阅内容。

## 新闻内容
{news_content}

## 输出要求

请以 JSON 格式输出分析结果，包含以下字段：
```json
{{
  "summary": "热点趋势概述（100-200字）",
  "keyword_analysis": "关键词热度分析",
  "sentiment": "情感倾向分析（积极/中性/消极）",
  "cross_platform": "跨平台关联分析",
  "signals": "值得关注的信号",
  "conclusion": "总结与建议"
}}
```"""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]

        # 解析 JSON 响应
        try:
            # 提取 JSON 部分
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content

            result = json.loads(json_str.strip())
            result["success"] = True
            result["raw_response"] = content
            return result

        except (json.JSONDecodeError, IndexError):
            # JSON 解析失败，返回原始文本
            return {
                "success": True,
                "summary": content[:1000],
                "raw_response": content,
                "parse_error": "无法解析 JSON 格式",
            }

    # ==================== 缓存管理 ====================

    def clear_all_cache(self):
        """清空所有缓存"""
        self.hotlist_fetcher.clear_cache()
        self.rss_cache.clear_all()
        self.ai_cache.clear_all()

    def clear_expired_cache(self):
        """清理过期缓存"""
        self.hotlist_fetcher.cache.clear_expired()
        self.rss_cache.clear_expired()
        self.ai_cache.clear_expired()


# 单例实例
_service_instance: Optional[TrendRadarService] = None


def get_trendradar_service() -> TrendRadarService:
    """获取 TrendRadar 服务单例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = TrendRadarService()
    return _service_instance
