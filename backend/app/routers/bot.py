"""
FinanceSim Bot Router
Bot 交易员 API
"""
from typing import List, Optional
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
    trading_engine_ref: str = Query("main"),
    tickers: List[str] = Query(["AAPL", "GOOGL", "MSFT"]),
    market_data: dict = Body({})
):
    if not _bot_engine:
        return {"error": "Bot engine not initialized"}
    
    trades = _bot_engine.step(None, tickers, market_data)
    return {"trades": len(trades), "recent_trades": trades[-10:]}


@router.get("/trades")
async def get_recent_trades(limit: int = Query(50, le=200)):
    if not _bot_engine:
        return {"error": "Bot engine not initialized"}
    return _bot_engine.trade_log[-limit:]
