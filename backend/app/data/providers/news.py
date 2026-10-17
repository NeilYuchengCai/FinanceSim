"""
新闻 provider（NewsAPI 兼容）

仅在 ``settings.NEWS_API_KEY`` 非空时启用（``enabled = bool(key)``）。
默认对接 NewsAPI 的 ``/v2/everything`` 端点（``settings.NEWS_BASE_URL`` 可覆盖为
私有/兼容服务）。若想零 key 使用公开 RSS，可在部署时把 ``NEWS_BASE_URL`` 指向一个
RSS->JSON 代理，并相应调整 :meth:`fetch` 的解析分支（此处保持 NewsAPI JSON 解析）。

归一化输出（列表）：
    [{"headline": str, "body": str, "source": str, "ts": iso}, ...]

任何缺 key / 非 200 / 无文章 / 解析失败都抛 ``ProviderError``，由调用方回退到合成新闻。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.providers.base import BaseProvider, ProviderError


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


class NewsApiProvider(BaseProvider):
    name = "news_api"

    def __init__(self) -> None:
        self.api_key = settings.NEWS_API_KEY
        self.base_url = settings.NEWS_BASE_URL
        self.enabled = bool(self.api_key)
        # 新闻时效性短，缓存更短一些（取总开关的一半，至少 60s）
        cache_ttl = max(60, int(settings.EXTERNAL_CACHE_TTL_SECONDS // 2))
        super().__init__(timeout=10.0, max_retries=1, cache_ttl=cache_ttl)

    async def fetch(
        self,
        query: str = "finance OR markets OR economy",
        language: str = "en",
        sort_by: str = "publishedAt",
        limit: int = 20,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            raise ProviderError("NewsAPI provider disabled (no API key)")

        params = {
            "apiKey": self.api_key,
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(int(limit), 100),
        }
        data = (
            await self._request("GET", f"{self.base_url}/everything", params=params)
        ).json()

        status = (data or {}).get("status")
        if status == "error":
            raise ProviderError(f"NewsAPI error: {data.get('message')}")
        articles = (data or {}).get("articles") or []
        out: List[Dict[str, Any]] = []
        for art in articles[: int(limit)]:
            if not isinstance(art, dict):
                continue
            source_name = (art.get("source") or {}).get("name") or "NEWS_API"
            out.append({
                "headline": art.get("title") or "",
                "body": art.get("description") or art.get("content") or "",
                "source": source_name,
                "ts": art.get("publishedAt") or _utc_iso(),
            })

        if not out:
            raise ProviderError("NewsAPI: no articles returned")
        return out
