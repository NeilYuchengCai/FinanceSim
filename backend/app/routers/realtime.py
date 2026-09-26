"""
FinanceSim 实时行情 WebSocket 路由

端点：ws://<host>/api/v1/ws/prices

消息契约（前端按此对接，字段名不要改）：
  首帧  {"type":"snapshot","ts":"2026-09-26T01:00:00","items":[{"t":"AAPL","p":178.53,"c":0.32}]}
  增量  {"type":"update","ts":"2026-09-26T01:00:01","items":[{"t":"AAPL","p":178.61,"c":0.36}]}
其中 t=ticker，p=最新价（数字），c=相对前收的涨跌幅百分比（数字，不是字符串）。
增量帧只推送发生变化的条目；休市时 items 为空数组（兼作心跳）。
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.market_stream import get_market_stream, _utc_iso

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])

# 客户端长时间无消息时也保证至少有一次下行流量（休市/无变化时由 tick 帧承担）
HEARTBEAT_SECONDS = 15.0


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    await websocket.accept()

    stream = get_market_stream()
    queue = stream.subscribe()
    try:
        # 1) 连接建立后先发全量快照
        await websocket.send_text(json.dumps({
            "type": "snapshot",
            "ts": _utc_iso(),
            "items": stream.snapshot_items(),
        }))

        # 2) 之后持续推送增量
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                payload = {"type": "update", "ts": _utc_iso(), "items": []}
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Price websocket closed unexpectedly")
    finally:
        stream.unsubscribe(queue)
