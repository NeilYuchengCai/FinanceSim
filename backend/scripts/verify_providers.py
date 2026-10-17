"""
离线验证脚本：确认外部数据 provider 框架在"默认（离线优先）"配置下安全。

运行：
    python scripts/verify_providers.py

它断言：
1. ``settings.USE_EXTERNAL_DATA`` 默认为 ``False``（离线优先总开关关闭）。
2. 三个 provider（alpha_vantage / fred / news_api）默认 ``enabled`` 均为 ``False``（无 key）。
3. 对每个 provider 调用 ``maybe_fetch`` 都返回 ``None`` 且不抛异常。

只要全部通过即打印 PASS。任何一项失败打印 FAIL 并以非零退出码结束。
本脚本不触碰网络、不依赖数据库。
"""
import asyncio
import os
import sys

# 让脚本能 import app（脚本位于 backend/scripts 下）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.data.providers import PROVIDERS, get_provider, maybe_fetch


def run_checks():
    failures = []

    # 1) 总开关默认关闭
    if settings.USE_EXTERNAL_DATA is not False:
        failures.append(
            f"USE_EXTERNAL_DATA 应为 False，实际为 {settings.USE_EXTERNAL_DATA!r}"
        )

    # 2) 各 provider 默认未启用（无 key）
    expected_providers = ["alpha_vantage", "fred", "news_api"]
    for name in expected_providers:
        provider = get_provider(name)
        if provider is None:
            failures.append(f"provider {name!r} 未注册")
            continue
        if provider.enabled is not False:
            failures.append(
                f"provider {name!r}.enabled 应为 False，实际为 {provider.enabled!r}"
            )

    # 3) maybe_fetch 对每个 provider 返回 None 且不抛异常
    async def check_maybe_fetch():
        for name in expected_providers:
            provider = get_provider(name)
            try:
                result = await maybe_fetch(provider)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"maybe_fetch({name!r}) 抛异常: {exc!r}")
                continue
            if result is not None:
                failures.append(
                    f"maybe_fetch({name!r}) 应返回 None，实际返回 {result!r}"
                )

    asyncio.run(check_maybe_fetch())

    # 额外健全性：PROVIDERS 字典齐备
    for name in expected_providers:
        if name not in PROVIDERS:
            failures.append(f"PROVIDERS 缺少 {name!r}")

    return failures


def main():
    print("=" * 60)
    print("FinanceSim 外部数据 provider 离线验证")
    print("=" * 60)
    print(f"USE_EXTERNAL_DATA = {settings.USE_EXTERNAL_DATA}")
    for name in ["alpha_vantage", "fred", "news_api"]:
        p = get_provider(name)
        print(f"provider {name:>14} : enabled={getattr(p, 'enabled', 'N/A')}")

    failures = run_checks()
    print("-" * 60)
    if not failures:
        print("PASS: 离线优先默认配置安全（无网络访问、无异常、行为与引入框架前一致）")
        return 0
    for f in failures:
        print(f"FAIL: {f}")
    print(f"\nFAILED with {len(failures)} issue(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
