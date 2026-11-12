"""
Alpha Vantage 价格 provider（兼容免 key 模式）

启用优先级（OFFLINE-FIRST）：
- 若 ``settings.ALPHA_VANTAGE_API_KEY`` 非空 → 走官方 Alpha Vantage 接口（GLOBAL_QUOTE / FX_DAILY）。
- 若未填 key（默认）→ 自动走免 key 数据源：
  * 股票 / ETF / 指数：CNBC 公开行情接口（单标的，无需 key）。
  * 外汇对：Frankfurter（ECB 参考汇率，一次请求覆盖全部主要货币交叉盘，无需 key）。

任一数据源可用即 ``enabled=True``；总开关 ``USE_EXTERNAL_DATA`` 关闭时由调用方回退。
所有异常（缺网络 / 非 200 / 限额 / 解析失败）都被收敛为 ``None`` 或部分结果，绝不抛给主流程。

归一化输出（与上游 ``market_stream._maybe_seed_live_prices`` 完全兼容）：
    {"SYMBOL": {"price": float, "currency": "USD", "ts": iso}}
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.data.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

_NUM_RE = re.compile(r"[-+]?\d*\.?\d+")
# Frankfurter 支持的货币（ECB 参考汇率覆盖集）
_FX_SUPPORTED = {
    "AUD", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD", "HUF",
    "ISK", "JPY", "KRW", "MXN", "NOK", "NZD", "PLN", "RON", "SEK", "SGD",
    "THB", "TRY", "USD", "ZAR",
}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def _clean_number(s: Any) -> Optional[float]:
    """从 CNBC 等返回的字符串里抠出浮点数（容忍 $、逗号、N/A）。"""
    if s is None:
        return None
    s = str(s).replace(",", "").replace("$", "").strip()
    if s in ("", "N/A", "NA", "None", "null"):
        return None
    m = _NUM_RE.search(s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


class AlphaVantagePriceProvider(BaseProvider):
    name = "alpha_vantage"

    def __init__(self) -> None:
        self.api_key = settings.ALPHA_VANTAGE_API_KEY
        self.base_url = settings.ALPHA_VANTAGE_BASE_URL
        self.cnbc_url = settings.CNBC_QUOTE_URL
        self.frankfurter_url = settings.FRANKFURTER_URL
        # 有 key 走 AlphaVantage；无 key 走免 key 源。两者任一可用即启用。
        self.keyless = bool(self.cnbc_url or self.frankfurter_url)
        self.enabled = bool(self.api_key) or self.keyless
        self.price_cap = max(1, int(settings.KEYLESS_PRICE_MAX))
        self.concurrency = max(1, int(settings.KEYLESS_PRICE_CONCURRENCY))
        self.batch_delay = float(settings.KEYLESS_PRICE_BATCH_DELAY)
        super().__init__(
            timeout=10.0,
            max_retries=2,
            cache_ttl=settings.EXTERNAL_CACHE_TTL_SECONDS,
        )

    def _is_fx(self, symbol: str) -> bool:
        return "/" in str(symbol)

    async def fetch(self, symbols=None, **kwargs: Any) -> Dict[str, Dict[str, Any]]:
        if not self.enabled:
            raise ProviderError("price provider disabled (no key and no keyless source)")
        if symbols is None:
            symbols = []
        if isinstance(symbols, str):
            symbols = [symbols]
        if self.api_key:
            return await self._fetch_keyed(symbols)
        return await self._fetch_keyless(symbols)

    # ---------------------------------------------------------- 免 key 路径
    async def _fetch_keyless(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        fx, eq = [], []
        for s in symbols:
            s = str(s).upper().strip()
            if not s:
                continue
            (fx if self._is_fx(s) else eq).append(s)

        result: Dict[str, Dict[str, Any]] = {}
        # 外汇：一次 Frankfurter 请求覆盖全部交叉盘
        try:
            result.update(await self._fetch_fx_keyless(fx))
        except Exception as exc:  # 绝不影响主流程
            logger.debug("keyless FX fetch failed: %s", exc)

        # 股票/ETF/指数：CNBC 单标的并发抓取（限量节流，避免过度请求）
        eq = eq[: self.price_cap]
        sem = asyncio.Semaphore(self.concurrency)

        async def _one(sym: str) -> None:
            async with sem:
                try:
                    q = await self._fetch_cnbc_one(sym)
                except Exception as exc:
                    logger.debug("CNBC keyless fetch failed for %s: %s", sym, exc)
                    q = None
                if q is not None:
                    result[sym] = q
                if self.batch_delay:
                    await asyncio.sleep(self.batch_delay)

        await asyncio.gather(*[_one(s) for s in eq])
        return result

    async def _fetch_cnbc_one(self, symbol: str) -> Optional[Dict[str, Any]]:
        cache_key = f"cnbc:{symbol}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        params = {
            "symbols": symbol,
            "requestMethod": "ext",
            "noform": "1",
            "partnerId": "2",
            "fund": "1",
            "exthrs": "0",
            "output": "json",
        }
        resp = await self._request("GET", self.cnbc_url, params=params)
        data = resp.json()
        arr = (data or {}).get("QuickQuoteResult", {}).get("QuickQuote") or []
        if not arr:
            return None
        item = arr[0]
        price = _clean_number(item.get("last"))
        if price is None or price <= 0:
            return None
        ts = item.get("last_time") or _utc_iso()
        out = {"price": price, "currency": "USD", "ts": ts}
        self._cache_set(cache_key, out)
        return out

    async def _fetch_fx_keyless(self, fx_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        if not fx_symbols:
            return {}
        codes: set = set()
        for s in fx_symbols:
            a, b = s.split("/", 1)
            codes.add(a.upper())
            codes.add(b.upper())
        wanted = [c for c in codes if c in _FX_SUPPORTED and c != "USD"]
        if not wanted:
            return {}
        cache_key = "frankfurter:" + ",".join(sorted(wanted))
        cached = self._cache_get(cache_key)
        if cached is not None:
            rates = cached
        else:
            params = {"base": "USD", "symbols": ",".join(wanted)}
            resp = await self._request("GET", self.frankfurter_url, params=params)
            j = resp.json()
            rates = j.get("rates") or {}
            self._cache_set(cache_key, rates)
        if not rates:
            return {}

        result: Dict[str, Dict[str, Any]] = {}
        ts = _utc_iso()
        for s in fx_symbols:
            a, b = s.split("/", 1)
            a, b = a.upper(), b.upper()
            if a not in _FX_SUPPORTED or b not in _FX_SUPPORTED:
                continue
            ra = rates.get(a) if a != "USD" else 1.0
            rb = rates.get(b) if b != "USD" else 1.0
            if ra is None or rb is None or ra <= 0 or rb <= 0:
                continue
            # Frankfurter 给的是「每 1 USD 多少 X」；pair=BASE/QUOTE 价格 = 每 1 BASE 多少 QUOTE
            price = rb / ra
            result[s] = {"price": round(price, 6), "currency": b, "ts": ts}
        return result

    # ---------------------------------------------------------- keyed 路径（有 key 时优先）
    async def _fetch_keyed(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        # 有 key 时仍限量，避免触发 AlphaVantage 免费档（5 次/分）限额导致大量失败。
        capped = symbols[: max(25, self.price_cap)]
        result: Dict[str, Dict[str, Any]] = {}
        for sym in capped:
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
        note = data.get("Note") or data.get("Information") or data.get("Error Message")
        if note:
            raise ProviderError(f"AlphaVantage: {note}")
        quote = (data or {}).get("Global Quote") or {}
        price = quote.get("05. price")
        if price is None:
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
        latest_day = max(series.keys())
        close = (series[latest_day] or {}).get("4. close")
        if close is None:
            return None
        try:
            price = float(close)
        except (TypeError, ValueError) as exc:
            raise ProviderError(f"AlphaVantage: bad FX price for {symbol}: {close}") from exc
        return {"price": price, "currency": to_sym, "ts": latest_day}
