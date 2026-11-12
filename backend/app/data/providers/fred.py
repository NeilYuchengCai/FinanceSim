"""
FRED 宏观数据 provider（兼容免 key 模式）

启用优先级（OFFLINE-FIRST）：
- 若 ``settings.FRED_API_KEY`` 非空 → 走官方 FRED ``/series/observations``（keyed）。
- 若未填 key（默认）→ 自动走 FRED 公开 CSV 下载端点（``fredgraph.csv``，无需 key）。

免 key 路径的归一化输出与 keyed 路径**完全同构**，因此上游
``economic_engine.apply_fred_series`` 无需任何改动即可消费：
    {"series_id": [{"date": "2026-09-01", "value": 3.1}, ...]}  # 按日期降序

任何缺网络 / 非 200 / 无观测 / 解析失败都抛 ``ProviderError`` 或被收敛为部分/空结果，
由调用方回退到合成宏观状态。
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)


class FredMacroProvider(BaseProvider):
    name = "fred"

    def __init__(self) -> None:
        self.api_key = settings.FRED_API_KEY
        self.base_url = settings.FRED_BASE_URL
        self.csv_url = settings.FRED_CSV_URL
        self.keyless = bool(self.csv_url)
        self.enabled = bool(self.api_key) or self.keyless
        super().__init__(
            timeout=10.0,
            max_retries=2,
            cache_ttl=settings.EXTERNAL_CACHE_TTL_SECONDS,
        )

    async def fetch(self, series_ids=None, limit: int = 12, **kwargs: Any) -> Dict[str, List[Dict[str, Any]]]:
        if not self.enabled:
            raise ProviderError("FRED provider disabled (no key and no keyless source)")
        if series_ids is None:
            series_ids = []
        if isinstance(series_ids, str):
            series_ids = [series_ids]
        if self.api_key:
            return await self._fetch_keyed(series_ids, limit)
        return await self._fetch_keyless(series_ids, limit)

    # ---------------------------------------------------------- 免 key 路径（FRED CSV）
    async def _fetch_keyless(self, series_ids, limit: int) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}
        for sid in series_ids:
            sid = str(sid).strip()
            if not sid:
                continue
            cache_key = f"fredcsv:{sid}:{limit}"
            cached = self._cache_get(cache_key)
            if cached is not None:
                result[sid] = cached
                continue
            series = await self._fetch_csv_one(sid, limit)
            if series:
                self._cache_set(cache_key, series)
                result[sid] = series
        if not result:
            raise ProviderError("FRED keyless: no series resolved")
        return result

    async def _fetch_csv_one(self, series_id: str, limit: int) -> List[Dict[str, Any]]:
        # 取足够长的时间窗（约 limit*40 天 + 余量），保证至少有 limit 个观测点。
        start = (datetime.now() - timedelta(days=int(limit) * 40 + 200)).strftime("%Y-%m-%d")
        params = {"id": series_id, "cosd": start}
        try:
            resp = await self._request("GET", self.csv_url, params=params)
            text = resp.text
        except Exception as exc:
            logger.debug("FRED CSV request failed for %s: %s", series_id, exc)
            return []

        rows: List[Dict[str, Any]] = []
        try:
            reader = csv.reader(io.StringIO(text))
            header = next(reader, None)
            if not header or len(header) < 2:
                return []
            for row in reader:
                if len(row) < 2:
                    continue
                date = row[0].strip()
                val = row[1].strip()
                if val in ("", ".", "NaN"):
                    continue
                try:
                    v = float(val)
                except ValueError:
                    continue
                # FRED 对利率/失业率偶尔以 0 占位，跳过以免污染状态。
                if v == 0.0 and series_id in ("FEDFUNDS", "UNRATE"):
                    continue
                rows.append({"date": date, "value": v})
        except Exception as exc:
            logger.debug("FRED CSV parse failed for %s: %s", series_id, exc)
            return []

        if not rows:
            return []
        # CSV 为升序（最旧在前）→ 翻转为降序（最新在前），与 keyed 路径一致。
        rows.reverse()
        return rows[: int(limit)]

    # ---------------------------------------------------------- keyed 路径（有 key 时优先）
    async def _fetch_keyed(self, series_ids, limit: int) -> Dict[str, List[Dict[str, Any]]]:
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
