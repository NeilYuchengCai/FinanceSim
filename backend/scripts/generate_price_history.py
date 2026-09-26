"""
FinanceSim — 价格历史生成脚本

用几何布朗运动(GBM)为每个资产生成一段 OHLCV 历史，并把最后一根收盘价
锚定到该资产的 current_price，使历史与当前报价衔接。

为每个需要历史行情的资产生成一段 OHLCV 时间序列。

用法:
    python generate_price_history.py             # 默认 90 个交易日
    python generate_price_history.py --days 180  # 指定天数
"""
import json
import math
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(HERE, "..", "financesim.db"))

# 需要与价格历史挂钩的资产类型（FX/BOND 的价格由各自的引擎在内存中维护）
HISTORY_TYPES = ("EQUITY", "ETF", "INDEX")

SEED = 20260926


def pick_step(asset_id: int, i: int, vol: float, drift: float, rng: random.Random) -> float:
    """单步收益率 - Box-Muller 正态抽样"""
    u1 = max(rng.random(), 1e-12)
    u2 = rng.random()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return drift + vol * z


def round_px(px: float, currency: str) -> float:
    """按币种习惯取整

    日元/韩元/印尼盾等无小数位，其余保留两位小数。
    """
    if currency in ("JPY", "KRW", "IDR", "VND", "CLP", "COP", "HUF"):
        return float(round(px))
    if px < 1:  # 汇率、低价股
        return float(round(px, 5))
    return float(round(px, 2))


def round_volume(base: float, rng: random.Random) -> int:
    return max(1, int(base * rng.uniform(0.6, 1.5)))


def main():
    days = 90
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    assets = cur.execute(
        """SELECT id, ticker, currency, current_price, volatility, market_cap, type
           FROM assets WHERE type IN (?,?,?) ORDER BY id""",
        HISTORY_TYPES,
    ).fetchall()

    total = len(assets)
    print(f"需要生成历史的资产: {total}，每个 {days} 个交易日")

    if total == 0:
        print("没有需要处理的资产")
        conn.close()
        return 1

    # 清空旧历史，避免重复插入
    cur.execute("DELETE FROM price_history")
    conn.commit()

    rng = random.Random(SEED)
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)

    inserted = 0
    batch = []

    for asset_id, ticker, currency, price, vol, mcap, atype in assets:
        if not price or price <= 0:
            # 没有当前价格的资产无法生成有意义的路径，跳过
            continue

        vol = vol or 0.25
        # 日波动 = 年化波动 / sqrt(252)
        daily_vol = vol / math.sqrt(252.0)
        drift = 0.0002  # 轻微正漂移

        # 正向生成一条路径（起点为 1.0 的相对价格）
        path = [1.0]
        for i in range(days):
            r = pick_step(asset_id, i, daily_vol, drift, rng)
            path.append(path[-1] * math.exp(r))

        # 缩放使最后一根收盘价等于 current_price
        scale = price / path[-1]

        # 成交量按换手率估算：日均成交量 ≈ 流通股数 × 换手率。
        # 直接用市值线性缩放会让所有标的挤在同一量级，活跃榜失去区分度。
        shares = (mcap * 1e6 / price) if (mcap and price) else 0.0
        base_volume = shares * 0.005 if shares else 100_000.0
        base_volume = max(1_000.0, min(base_volume, 2e8))

        prev_close = None
        for i, rel in enumerate(path):
            # 第 0 根作为开盘基准，不写入；从 i=1 开始写入 K 线
            if i == 0:
                prev_close = rel * scale
                continue

            ts = start_date + timedelta(days=i)
            close = rel * scale
            open_px = prev_close
            # 日内高低点
            intraday = daily_vol * abs(rng.gauss(0, 1)) * 0.8
            high = max(open_px, close) * (1.0 + intraday)
            low = min(open_px, close) * (1.0 - intraday)
            low = max(low, 0.0001)

            batch.append((
                asset_id,
                ts.isoformat(),
                round_px(open_px, currency),
                round_px(high, currency),
                round_px(low, currency),
                round_px(close, currency),
                round_volume(base_volume, rng),
                "SIMULATED",          # data_source：明确标注为模拟数据
                None,                 # source_ts
                i - days,             # world_day（相对天数）
            ))
            prev_close = close
            inserted += 1

            if len(batch) >= 5000:
                cur.executemany(
                    """INSERT INTO price_history
                       (asset_id, timestamp, open, high, low, close, volume,
                        data_source, source_ts, world_day)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    batch,
                )
                conn.commit()
                batch = []
                print(f"  ... 已写入 {inserted} 行", flush=True)

    if batch:
        cur.executemany(
            """INSERT INTO price_history
               (asset_id, timestamp, open, high, low, close, volume,
                data_source, source_ts, world_day)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            batch,
        )
        conn.commit()

    print(f"\n写入完成: {inserted} 行 K 线")

    rows = cur.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
    d = cur.execute("SELECT COUNT(DISTINCT asset_id) FROM price_history").fetchone()[0]
    print(f"price_history 总计: {rows} 行，覆盖 {d} 个资产")

    # 抽样校验：最后一日的收盘价应等于 current_price
    print("\n锚点校验（最后收盘价 vs current_price）:")
    cur.execute(
        """SELECT a.ticker, a.currency, a.current_price,
                  (SELECT close FROM price_history p WHERE p.asset_id=a.id
                   ORDER BY p.timestamp DESC LIMIT 1) AS last_close
           FROM assets a
           WHERE a.id IN (SELECT DISTINCT asset_id FROM price_history)
           LIMIT 6"""
    )
    for tk, ccy, want, got in cur.fetchall():
        diff = abs(got - want) / want * 100 if want else 0
        print(f"  {tk:12s} {ccy} current={want:>12} last_close={got:>12} diff={diff:.4f}%")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
