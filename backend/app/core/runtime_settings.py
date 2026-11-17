"""
运行时数据源选择（前端设置页 -> 后端即时生效）

把用户在设置页选中的"数据源"映射为后端行为：
- ``fallback``（内置数据）            -> 仅内置合成数据（``USE_EXTERNAL_DATA=False``）
- 其它（alpha-vantage/fred/frankfurter）-> 启用外部真实数据（``USE_EXTERNAL_DATA=True``）

关键事实：后端各 provider（价格 / 宏观 / 新闻）**已内置免 key 模式**
（股票·ETF·指数走 CNBC、外汇走 Frankfurter、宏观走 FRED 公开 CSV、新闻走 RSS），
因此开启外部数据后**即使不填任何 API key 也能拉到真实行情**；任意网络/解析失败
都会由 ``maybe_fetch`` 自动回退到合成数据（OFFLINE-FIRST 不变）。

设置变更即时生效：开启外部数据时立即触发一次实时价格重播种（若行情流已运行）。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.config import settings
from app.data.providers import get_provider

logger = logging.getLogger(__name__)

# 与 frontend/src/hooks/useSettings.ts 的 DATA_SOURCE_OPTIONS 保持一致
_FALLBACK = "fallback"
_VALID = {"fallback", "alpha-vantage", "fred", "frankfurter"}

_current: str = _FALLBACK


def set_data_source(source: str) -> str:
    """设置数据源并即时应用到后端全局开关。返回实际生效值。"""
    global _current
    if source not in _VALID:
        source = _FALLBACK
    _current = source
    # 翻转全局开关：任何非 fallback 选项都启用外部真实数据接入
    settings.USE_EXTERNAL_DATA = source != _FALLBACK
    logger.info(
        "Data source set to %s (USE_EXTERNAL_DATA=%s)",
        source, settings.USE_EXTERNAL_DATA,
    )
    # 开启外部数据时，触发一次实时价格重播种（若行情流已运行）
    if settings.USE_EXTERNAL_DATA:
        try:
            from app.services.market_stream import get_market_stream

            stream = get_market_stream()
            if getattr(stream, "_running", False):
                asyncio.create_task(stream.reseed_live_prices())
        except Exception as exc:  # 绝不影响设置保存
            logger.warning("Failed to trigger live reseed: %s", exc)
    return _current


def get_data_source() -> str:
    return _current


def get_availability() -> Dict[str, Any]:
    """返回各外部源可用性，供前端展示（enabled / keyed / 模式）。"""
    out: Dict[str, Any] = {}
    for name in ("alpha_vantage", "fred", "news_api"):
        p = get_provider(name)
        enabled = bool(getattr(p, "enabled", False))
        keyed = bool(getattr(p, "api_key", None))
        out[name] = {
            "enabled": enabled,
            "keyed": keyed,
            "mode": "keyed" if keyed else ("keyless" if enabled else "disabled"),
        }
    return out
