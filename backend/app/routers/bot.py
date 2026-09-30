"""
FinanceSim Bot Router
Bot 交易员 API
"""
import random
from typing import Dict, List, Optional
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

from app.engines import BotEngine, BotConfig

router = APIRouter(prefix="/bots", tags=["bots"])

_bot_engine: Optional[BotEngine] = None


def init_bot_engine(engine: BotEngine):
    global _bot_engine
    _bot_engine = engine


class AddBotRequest(BaseModel):
    name: str
    strategy: str = "momentum"  # momentum, mean_reversion, market_making, random
    risk_tolerance: float = 0.5
    capital: float = 100000.0
    max_position_size: float = 1000.0


@router.get("/stats")
async def get_stats():
    if not _bot_engine:
        return {"error": "Bot engine not initialized"}
    return _bot_engine.get_stats()


@router.post("/add")
async def add_bot(req: AddBotRequest):
    if not _bot_engine:
        return {"error": "Bot engine not initialized"}
    
    config = BotConfig(
        name=req.name,
        strategy=req.strategy,
        risk_tolerance=req.risk_tolerance,
        capital=req.capital,
        max_position_size=req.max_position_size
    )
    _bot_engine.add_bot(config)
    return {"success": True, "name": req.name}


@router.delete("/remove/{name}")
async def remove_bot(name: str):
    if not _bot_engine:
        return {"error": "Bot engine not initialized"}
    success = _bot_engine.remove_bot(name)
    return {"success": success}


@router.post("/step")
async def step_bots(
    world_id: int = Query(1),
    tickers: List[str] = Query(default_factory=lambda: ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "JPM", "XOM"])
):
    if not _bot_engine:
        return {"error": "Bot engine not initialized"}
    trades = run_bots_for_world(world_id, tickers)
    return {"trades": len(trades), "recent_trades": trades[-10:]}


def run_bots_for_world(world_id: int, tickers: Optional[List[str]] = None) -> List[Dict]:
    """用真实交易引擎 + 实时行情驱动 AI 交易员，返回本次成交。"""
    if not _bot_engine:
        return []
    from app.routers.trading import get_trading_engine
    from app.services.market_stream import get_market_stream

    trading_engine = get_trading_engine(world_id)
    stream = get_market_stream()
    market_data: Dict[str, Dict] = {}
    if stream is not None:
        for st in stream.snapshot_full():
            market_data[st["t"]] = {"price": st["p"]}

    # 注入真实宏观状态，供 macro 策略决策（缺失时退化为空字典不影响其他策略）
    try:
        from app.routers.economy import _economic_engine
        if _economic_engine is not None:
            market_data["macro"] = _economic_engine.get_macro_data()
    except Exception:
        pass

    if not tickers:
        all_t = list(market_data.keys())
        random.shuffle(all_t)
        tickers = all_t[:40]

    return _bot_engine.step(trading_engine, tickers, market_data)


@router.get("/trades")
async def get_recent_trades(limit: int = Query(50, le=200)):
    if not _bot_engine:
        return {"error": "Bot engine not initialized"}
    return _bot_engine.trade_log[-limit:]
