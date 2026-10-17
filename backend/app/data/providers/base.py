"""
Provider 抽象基类与异常

设计目标（OFFLINE-FIRST）：
- 每个 provider 都是"可选的、可失败的"数据来源。调用方在拿到数据前永远不信任它，
  任何异常（缺 key / 网络错误 / 非 200 / 解析失败）都被收敛成 ``ProviderError``，
  由上层 ``maybe_fetch`` 捕获后静默回退到合成/历史数据。
- 轻依赖：仅用标准库 + 已存在于 requirements.txt 的 ``httpx``。无其它第三方依赖。
- 内置：超时、有限重试（1~2 次）、基于 ``time.monotonic()`` 的内存 TTL 缓存。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Provider 无法满足条件时抛出（缺 key / 网络 / 非 200 / 解析失败）。

    调用方约定：捕获此异常即代表"数据源不可用"，应回退到本地合成/缓存数据。
    """


class BaseProvider:
    """外部数据 provider 的抽象基类。

    子类必须实现 :meth:`fetch`，并（推荐）在 ``__init__`` 中根据配置设置 ``enabled``。
    基类提供：
    - HTTP 请求封装 ``_request``（带超时 + 有限重试，非 200 抛 ``ProviderError``）
    - 内存 TTL 缓存 ``_cache_get`` / ``_cache_set``（按 query 字符串缓存）
    """

    #: provider 唯一名（用于注册表与日志）
    name: str = "base"
    #: 是否启用（默认 False；子类通常按"是否有 key"决定）
    enabled: bool = False
    #: 单次请求超时（秒）
    timeout: float = 10.0
    #: 最大尝试次数（含首次）
    max_retries: int = 2

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 2,
        cache_ttl: float = 300.0,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[float, Any]] = {}

    # -------------------------------------------------------------- 缓存
    def _cache_get(self, key: str) -> Optional[Any]:
        item = self._cache.get(key)
        if item is None:
            return None
        ts, value = item
        if time.monotonic() - ts > self.cache_ttl:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value: Any) -> None:
        self._cache[key] = (time.monotonic(), value)

    def _cache_key(self, **kwargs: Any) -> str:
        """默认缓存键：把 fetch 的关键字参数稳定序列化。子类可覆盖。"""
        return "&".join(f"{k}={kwargs[k]}" for k in sorted(kwargs))

    # -------------------------------------------------------------- 请求
    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """带超时 + 有限重试的 HTTP 请求。

        非 200 视为失败并抛 ``ProviderError``（不重试语义错误，但网络抖动会重试）。
        """
        last_err: Optional[Exception] = None
        for attempt in range(1, max(self.max_retries, 1) + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.request(method, url, **kwargs)
                if resp.status_code != 200:
                    raise ProviderError(
                        f"{self.name}: HTTP {resp.status_code} for {url}"
                    )
                return resp
            except ProviderError:
                # 语义错误（非 200）不再重试，直接上抛
                raise
            except Exception as exc:  # 网络/超时等可重试错误
                last_err = exc
                logger.warning(
                    "%s request attempt %d/%d failed: %s",
                    self.name, attempt, self.max_retries, exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(0.2 * attempt)
        raise ProviderError(
            f"{self.name}: request failed after {self.max_retries} attempts: {last_err}"
        )

    # -------------------------------------------------------------- 接口
    async def fetch(self, **kwargs: Any) -> Any:
        """拉取并归一化数据。

        成功返回归一化后的 Python 对象；任何失败抛 :class:`ProviderError`，
        由上层 ``maybe_fetch`` 捕获并回退。子类必须实现。
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.fetch() must be implemented"
        )
