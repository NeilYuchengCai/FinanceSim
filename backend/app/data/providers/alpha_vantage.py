"""
Alpha Vantage 价格 provider

仅在 ``settings.ALPHA_VANTAGE_API_KEY`` 非空时启用（``enabled = bool(key)``）。
对外提供证券（GLOBAL_QUOTE）与外汇（FX_DAILY）两类报价：

- 证券：``function=GLOBAL_QUOTE&symbol=AAPL``，取 ``Global Quote`` 中的最新价。
- 外汇：``function=FX_DAILY&from_symbol=EUR&to_symbol=USD``，取最近一个交易日收盘。

归一化输出：
    {"SYMBOL": {"price": float, "currency": "USD", "ts": iso}}

任何缺 key / 非 200 / 限额(Note) / 解析失败都抛 ``ProviderError``，由调用方回退。
注意：离线优先，无 key 时本类 ``enabled=False``，``fetch`` 一上来就抛 ``ProviderError``。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import settings
from app.data.providers.base import BaseProvider, ProviderError


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


class AlphaVantagePriceProvider(BaseProvider):
    name = "alpha_vantage"

    def __init__(self) -> None:
        self.api_key = settings.ALPHA_VANTAGE_API_KEY
        self.base_url = settings.ALPHA_VANTAGE_BASE_URL
        self.enabled = bool(self.api_key)
        super().__init__(
            timeout=10.0,
            max_retries=2,
            cache_ttl=settings.EXTERNAL_CACHE_TTL_SECONDS,
        )

    def _is_fx(self, symbol: str) -> bool:
        # 形如 "EUR/USD" 视为外汇对
        return "/" in str(symbol)

    async def fetch(self, symbols=None, **kwargs: Any) -> Dict[str, Dict[str, Any]]:
        if not self.enabled:
            raise ProviderError("AlphaVantage provider disabled (no API key)")

        if symbols is None:
            symbols = []
        if isinstance(symbols, str):
            symbols = [symbols]

        result: Dict[str, Dict[str, Any]] = {}
        for sym in symbols:
            sym = str(sym).upper().strip()
            if not sym:
                continue
            cache_key = f"quote:{sym}"
            cached = self._cache_get(cache_key)
            if cached is not None:
                result[sym] = cached
                continue

            norm = await self._fetch_one(sym)
            if norm is not None:
                self._cache_set(cache_key, norm)
                result[sym] = norm
        return result

    async def _fetch_one(self, symbol: str) -> Optional[Dict[str, Any]]:
        if self._is_fx(symbol):
            return await self._fetch_fx(symbol)
        return await self._fetch_equity(symbol)

    async def _fetch_equity(self, symbol: str) -> Optional[Dict[str, Any]]:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key,
        }
        data = (await self._request("GET", self.base_url, params=params)).json()
        # 限额 / 提示信息
        note = data.get("Note") or data.get("Information") or data.get("Error Message")
        if note:
            raise ProviderError(f"AlphaVantage: {note}")
        quote = (data or {}).get("Global Quote") or {}
        price = quote.get("05. price")
        if price is None:
            # 空 quote：可能 symbol 不存在
            return None
        try:
            price = float(price)
        except (TypeError, ValueError) as exc:
            raise ProviderError(f"AlphaVantage: bad price for {symbol}: {price}") from exc
        ts = quote.get("07. latest trading day") or _utc_iso()
        return {"price": price, "currency": "USD", "ts": ts}

    async def _fetch_fx(self, symbol: str) -> Optional[Dict[str, Any]]:
        from_sym, to_sym = symbol.split("/", 1)
        params = {
            "function": "FX_DAILY",
            "from_symbol": from_sym,
            "to_symbol": to_sym,
            "apikey": self.api_key,
            "outputsize": "compact",
        }
        data = (await self._request("GET", self.base_url, params=params)).json()
        note = data.get("Note") or data.get("Information") or data.get("Error Message")
        if note:
            raise ProviderError(f"AlphaVantage: {note}")
        series = (data or {}).get("Time Series FX (Daily)") or {}
        if not series:
            return None
        # 字典键为日期，取最新一天
        latest_day = max(series.keys())
        close = (series[latest_day] or {}).get("4. close")
        if close is None:
            return None
        try:
            price = float(close)
        except (TypeError, ValueError) as exc:
            raise ProviderError(f"AlphaVantage: bad FX price for {symbol}: {close}") from exc
        return {"price": price, "currency": to_sym, "ts": latest_day}
