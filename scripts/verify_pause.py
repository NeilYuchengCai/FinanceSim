"""验证行情流在模拟暂停时冻结、恢复后继续推进。"""
import asyncio
import json
import time
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
WS = "ws://127.0.0.1:8000/api/v1/ws/prices"
WORLD = 1


def post(path):
    req = urllib.request.Request(BASE + path, data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


async def collect(seconds):
    import websockets
    items_total = 0
    paused_flags = set()
    prices = {}
    async with websockets.connect(WS) as ws:
        msg = json.loads(await asyncio.wait_for(ws.recv(), 5))
        for it in msg.get("items", []):
            prices[it["t"]] = it["p"]
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                raw = await asyncio.wait_for(ws.recv(), seconds)
            except asyncio.TimeoutError:
                break
            msg = json.loads(raw)
            paused_flags.add(msg.get("paused"))
            for it in msg.get("items", []):
                items_total += 1
                prices[it["t"]] = it["p"]
    return items_total, paused_flags, prices


async def main():
    # 先确保处于暂停态
    print("POST pause ->", post(f"/simulation/{WORLD}/pause"))
    await asyncio.sleep(1)

    items_paused, flags_paused, prices_paused = await collect(4)
    print("[PAUSED] items_total=%d paused_flags=%s" % (items_paused, flags_paused))

    # 恢复运行
    print("POST start ->", post(f"/simulation/{WORLD}/start"))
    await asyncio.sleep(1)

    items_run, flags_run, prices_run = await collect(5)
    print("[RUNNING] items_total=%d paused_flags=%s" % (items_run, flags_run))

    # 统计价格变化的标的数
    changed = sum(1 for t in set(prices_paused) & set(prices_run)
                  if prices_paused[t] != prices_run[t])

    print("\n=== RESULT ===")
    print("PAUSED: items should be ~0 -> %d" % items_paused)
    print("PAUSED: paused flag should be True -> %s" % (True in flags_paused and False not in flags_paused))
    print("RUNNING: items should be > 0 -> %d" % items_run)
    print("RUNNING: paused flag should be False -> %s" % (False in flags_run))
    print("PRICES CHANGED (running vs paused): %d tickers" % changed)

    ok = (items_paused <= 1 and True in flags_paused and items_run > 5 and changed > 0)
    print("VERIFY:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
