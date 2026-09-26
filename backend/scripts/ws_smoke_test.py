"""临时验证脚本：连 ws://127.0.0.1:8012/api/v1/ws/prices 收 5 秒消息并打印。

用法: python scripts/ws_smoke_test.py [seconds]
"""
import asyncio
import json
import sys
from collections import OrderedDict

import websockets

URL = "ws://127.0.0.1:8012/api/v1/ws/prices"
WATCH = ["AAPL", "MSFT", "NVDA"]


async def main(seconds: float):
    async with websockets.connect(URL) as ws:
        frames = []
        deadline = asyncio.get_event_loop().time() + seconds
        while asyncio.get_event_loop().time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=seconds + 2)
            except asyncio.TimeoutError:
                break
            frames.append(json.loads(raw))

    if not frames:
        print("NO FRAMES RECEIVED")
        return

    first = frames[0]
    print(f"frames received      : {len(frames)}")
    print(f"first frame type     : {first['type']}")
    print(f"first frame ts       : {first['ts']}")
    print(f"first frame items    : {len(first['items'])}")
    print(f"first frame sample   : {json.dumps(first['items'][:3], ensure_ascii=False)}")

    types = OrderedDict()
    for f in frames:
        types[f["type"]] = types.get(f["type"], 0) + 1
    print(f"frame types          : {dict(types)}")

    sizes = [len(json.dumps(f, ensure_ascii=False)) for f in frames]
    print(f"payload bytes        : min={min(sizes)} max={max(sizes)} "
          f"avg={sum(sizes)//len(sizes)}")

    # 校验契约
    bad = []
    for f in frames:
        if f["type"] not in ("snapshot", "update"):
            bad.append(f"bad type {f['type']}")
        if not isinstance(f.get("ts"), str):
            bad.append("ts not str")
        for it in f["items"]:
            if set(it.keys()) != {"t", "p", "c"}:
                bad.append(f"bad keys {it.keys()}")
                break
            if not isinstance(it["t"], str):
                bad.append("t not str")
            if not isinstance(it["p"], (int, float)) or isinstance(it["p"], bool):
                bad.append("p not number")
            if not isinstance(it["c"], (int, float)) or isinstance(it["c"], bool):
                bad.append("c not number")
            break
    print(f"contract check       : {'OK' if not bad else 'FAILED ' + str(bad[:5])}")

    # 追踪若干 ticker 的价格变化
    print("\n--- per-ticker price evolution ---")
    for tk in WATCH:
        series = []
        for f in frames:
            for it in f["items"]:
                if it["t"] == tk:
                    series.append((f["type"], it["p"], it["c"]))
        if not series:
            print(f"{tk}: not present in stream")
            continue
        shown = series[:8]
        print(f"{tk}:")
        for typ, p, c in shown:
            print(f"    [{typ:8}] p={p:<12} c={c}")
        prices = [p for _, p, _ in series]
        print(f"    -> {len(series)} ticks, first={prices[0]}, last={prices[-1]}, "
              f"distinct={len(set(prices))}, "
              f"max_abs_move_pct={max(abs((b - a) / a) * 100 for a, b in zip(prices, prices[1:])) if len(prices) > 1 else 0:.4f}")

    # 全局统计：一秒内最大单笔跳动
    all_moves = []
    prev = {}
    for f in frames[1:]:
        for it in f["items"]:
            old = prev.get(it["t"])
            if old:
                all_moves.append(abs(it["p"] - old) / old * 100)
            prev[it["t"]] = it["p"]
    if all_moves:
        all_moves.sort()
        print(f"\nper-tick move %%: p50={all_moves[len(all_moves)//2]:.4f} "
              f"p99={all_moves[int(len(all_moves)*0.99)]:.4f} max={all_moves[-1]:.4f}")

    last = frames[-1]
    print(f"\nlast frame: type={last['type']} ts={last['ts']} items={len(last['items'])}")
    print(f"last frame sample: {json.dumps(last['items'][:3], ensure_ascii=False)}")


if __name__ == "__main__":
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    asyncio.run(main(secs))
