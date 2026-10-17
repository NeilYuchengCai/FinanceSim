"""
外部数据 provider 注册表与统一入口

提供：
- ``PROVIDERS``：已知 provider 的实例字典（name -> instance），实例在导入时惰性创建。
- ``get_provider(name)``：按名取 provider 实例（不存在返回 ``None``）。
- ``maybe_fetch(provider, **kwargs)``：安全拉取——当 provider 为 ``None``、未启用、
  或总开关 ``settings.USE_EXTERNAL_DATA`` 关闭，或拉取抛 ``ProviderError`` / 任意异常时，
  一律返回 ``None``（并打印 warning），调用方据此回退到合成/历史数据。

离线优先保证：默认 ``USE_EXTERNAL_DATA=False`` 且所有 key 为空，因此 ``maybe_fetch``
对任何 provider 都直接返回 ``None``，绝不触碰网络，也绝不抛异常。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.config import settings
from app.data.providers.base import BaseProvider, ProviderError
from app.data.providers.alpha_vantage import AlphaVantagePriceProvider
from app.data.providers.fred import FredMacroProvider
from app.data.providers.news import NewsApiProvider

logger = logging.getLogger(__name__)

# name -> provider 类
_PROVIDER_CLASSES: Dict[str, type] = {
    "alpha_vantage": AlphaVantagePriceProvider,
    "fred": FredMacroProvider,
    "news_api": NewsApiProvider,
}

# name -> 已创建的单例实例（惰性）
_INSTANCES: Dict[str, BaseProvider] = {}


def get_provider(name: str) -> Optional[BaseProvider]:
    """按名获取 provider 实例；未知名称返回 ``None``。"""
    cls = _PROVIDER_CLASSES.get(name)
    if cls is None:
        return None
    inst = _INSTANCES.get(name)
    if inst is None:
        inst = cls()
        _INSTANCES[name] = inst
    return inst


# 已知 provider 实例字典（供测试/日志/调试直接检视 .enabled）
PROVIDERS: Dict[str, BaseProvider] = {
    name: get_provider(name)  # type: ignore[arg-type]
    for name in _PROVIDER_CLASSES
}


async def maybe_fetch(provider: Optional[BaseProvider], **kwargs: Any) -> Optional[Any]:
    """安全拉取外部数据。

    返回归一化数据；以下任一情况返回 ``None``（并打 warning，不抛异常）：
    - ``provider`` 为 ``None``
    - ``provider.enabled`` 为 ``False``（无 key）
    - 总开关 ``settings.USE_EXTERNAL_DATA`` 为 ``False``
    - ``provider.fetch`` 抛 ``ProviderError`` 或其它异常（网络/解析等）
    """
    if provider is None:
        logger.debug("maybe_fetch: no provider supplied, skipping")
        return None
    if not getattr(provider, "enabled", False):
        logger.debug("maybe_fetch: provider %s disabled, skipping", getattr(provider, "name", "?"))
        return None
    if not settings.USE_EXTERNAL_DATA:
        logger.debug("maybe_fetch: USE_EXTERNAL_DATA is off, skipping provider %s",
                     getattr(provider, "name", "?"))
        return None
    try:
        return await provider.fetch(**kwargs)
    except ProviderError as exc:
        logger.warning("Provider %s fetch failed, falling back: %s",
                       getattr(provider, "name", "?"), exc)
        return None
    except Exception as exc:  # 兜底：任何意外都不该影响主流程
        logger.warning("Provider %s unexpected error, falling back: %s",
                       getattr(provider, "name", "?"), exc)
        return None
