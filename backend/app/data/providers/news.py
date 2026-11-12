"""
新闻 provider（兼容免 key 模式）

启用优先级（OFFLINE-FIRST）：
- 若 ``settings.NEWS_API_KEY`` 非空 → 走 NewsAPI ``/v2/everything``（keyed）。
- 若未填 key（默认）→ 自动走免 key 的公开 RSS 源（stdlib 直接解析，无中间商，无 key）。

免 key 路径归一化输出与 keyed 路径**完全同构**，上游 ``news_engine.refresh_external_news``
无需改动即可消费：
    [{"headline": str, "body": str, "source": str, "ts": iso}, ...]

任何缺网络 / 非 200 / 无文章 / 解析失败都抛 ``ProviderError`` 或被收敛为部分/空结果，
由调用方回退到合成新闻。
"""
from __future__ import annotations

import email.utils
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_ENT_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def _strip_html(s: str) -> str:
    if not s:
        return ""
    s = _TAG_RE.sub(" ", s)
    s = _ENT_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_ts(s: Optional[str]) -> str:
    if not s:
        return _utc_iso()
    try:
        dt = email.utils.parsedate_to_datetime(s)
        if dt is not None:
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.isoformat(timespec="seconds")
    except Exception:
        pass
    return _utc_iso()


def _text(el: ET.Element, *tags: str) -> str:
    for t in tags:
        v = el.findtext(t)
        if v and v.strip():
            return v.strip()
    return ""


def _collect_items(root: ET.Element):
    items = root.findall(".//item")
    if items:
        return items, "rss"
    items = root.findall(".//entry")
    return items, "atom"


class NewsApiProvider(BaseProvider):
    name = "news_api"

    def __init__(self) -> None:
        self.api_key = settings.NEWS_API_KEY
        self.base_url = settings.NEWS_BASE_URL
        self.rss_feeds = [
            u.strip() for u in (settings.NEWS_RSS_FEEDS or "").split(",") if u.strip()
        ]
        self.keyless = bool(self.rss_feeds)
        self.enabled = bool(self.api_key) or self.keyless
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
            raise ProviderError("news provider disabled (no key and no RSS feed)")
        if self.api_key:
            return await self._fetch_keyed(query, language, sort_by, limit)
        return await self._fetch_rss(limit)

    # ---------------------------------------------------------- 免 key 路径（RSS）
    async def _fetch_rss(self, limit: int) -> List[Dict[str, Any]]:
        cache_key = "rss:" + ",".join(self.rss_feeds)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached[: int(limit)]

        out: List[Dict[str, Any]] = []
        seen: set = set()
        for feed in self.rss_feeds:
            if len(out) >= int(limit):
                break
            try:
                resp = await self._request("GET", feed)
                root = ET.fromstring(resp.text)
            except Exception as exc:
                logger.debug("RSS fetch/parse failed for %s: %s", feed, exc)
                continue

            items, kind = _collect_items(root)
            feed_title = ""
            if kind == "rss":
                ch = root.find(".//channel/title")
                if ch is not None and ch.text:
                    feed_title = ch.text.strip()
            else:
                ft = root.findtext(".//title")
                if ft:
                    feed_title = ft.strip()

            for it in items:
                if len(out) >= int(limit):
                    break
                headline = _text(it, "title")
                if not headline or headline in seen:
                    continue
                seen.add(headline)
                body = _strip_html(
                    _text(
                        it,
                        "description",
                        "summary",
                        "{http://purl.org/rss/1.0/modules/content/}encoded",
                    )
                )
                ts = _parse_ts(_text(it, "pubDate", "published", "updated"))
                src = _text(it, "source") or feed_title or "RSS"
                out.append({
                    "headline": headline,
                    "body": body,
                    "source": src,
                    "ts": ts,
                })

        if not out:
            raise ProviderError("RSS: no items from any feed")
        self._cache_set(cache_key, out)
        return out[: int(limit)]

    # ---------------------------------------------------------- keyed 路径（有 key 时优先）
    async def _fetch_keyed(self, query, language, sort_by, limit) -> List[Dict[str, Any]]:
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
