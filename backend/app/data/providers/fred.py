"""
FRED 宏观数据 provider

仅在 ``settings.FRED_API_KEY`` 非空时启用（``enabled = bool(key)``）。
调用 FRED ``/series/observations`` 拉取一个或多个宏观序列的最新观测值。

归一化输出：
    {"series_id": [{"date": "2026-09-01", "value": 3.1}, ...]}  # 按日期降序

任何缺 key / 非 200 / 无观测 / 解析失败都抛 ``ProviderError``，由调用方回退。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.providers.base import BaseProvider, ProviderError


class FredMacroProvider(BaseProvider):
    name = "fred"

    def __init__(self) -> None:
        self.api_key = settings.FRED_API_KEY
        self.base_url = settings.FRED_BASE_URL
        self.enabled = bool(self.api_key)
        super().__init__(
            timeout=10.0,
            max_retries=2,
            cache_ttl=settings.EXTERNAL_CACHE_TTL_SECONDS,
        )

    async def fetch(self, series_ids=None, limit: int = 12, **kwargs: Any) -> Dict[str, List[Dict[str, Any]]]:
        if not self.enabled:
            raise ProviderError("FRED provider disabled (no API key)")

        if series_ids is None:
            series_ids = []
        if isinstance(series_ids, str):
            series_ids = [series_ids]

        result: Dict[str, List[Dict[str, Any]]] = {}
        for sid in series_ids:
            sid = str(sid).strip()
            if not sid:
                continue
            cache_key = f"series:{sid}:{limit}"
            cached = self._cache_get(cache_key)
            if cached is not None:
                result[sid] = cached
                continue

            series = await self._fetch_one(sid, limit)
            self._cache_set(cache_key, series)
            result[sid] = series
        return result

    async def _fetch_one(self, series_id: str, limit: int) -> List[Dict[str, Any]]:
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": int(limit),
        }
        data = (
            await self._request("GET", f"{self.base_url}/series/observations", params=params)
        ).json()

        observations = (data or {}).get("observations") or []
        series: List[Dict[str, Any]] = []
        for obs in observations:
            raw = obs.get("value")
            # FRED 对缺失观测返回 "." 或空字符串
            if raw in (None, "", "."):
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            series.append({"date": obs.get("date"), "value": value})

        if not series:
            raise ProviderError(f"FRED: no usable observations for {series_id}")
        return series
