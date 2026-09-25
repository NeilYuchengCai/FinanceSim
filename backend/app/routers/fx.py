"""
FinanceSim FX Router
外汇市场 API
"""
from typing import Optional
from fastapi import APIRouter, Query

from app.engines import FXEngine

router = APIRouter(prefix="/fx", tags=["fx"])

_fx_engine: Optional[FXEngine] = None


def init_fx_engine(engine: FXEngine):
    """初始化外汇引擎实例"""
    global _fx_engine
    _fx_engine = engine


@router.get("/pairs")
async def list_pairs():
    """获取所有货币对"""
    if not _fx_engine:
        return {"error": "FX engine not initialized"}
    return _fx_engine.get_all_pairs()


@router.get("/pair/{ticker}")
async def get_pair(ticker: str):
    """获取单个货币对详情"""
    if not _fx_engine:
        return {"error": "FX engine not initialized"}
    
    pair = _fx_engine.get_pair(ticker)
    if not pair:
        return {"error": f"Pair {ticker} not found"}
    return pair.to_dict()


@router.get("/pair/{ticker}/history")
async def get_history(
    ticker: str,
    limit: int = Query(100, le=500)
):
    """获取历史价格"""
    if not _fx_engine:
        return {"error": "FX engine not initialized"}
    return _fx_engine.get_price_history(ticker, limit)


@router.post("/step")
async def step_fx(
    days: int = Query(1, ge=1, le=365),
    volatility_mult: float = Query(1.0, ge=0.1, le=5.0)
):
    """推进外汇市场"""
    if not _fx_engine:
        return {"error": "FX engine not initialized"}
    
    results = {}
    for _ in range(days):
        results = _fx_engine.step(volatility_mult)
    
    return results


@router.post("/shock")
async def apply_shock(
    shock_type: str = Query(..., pattern="^(central_bank|crisis|trade_war|pandemic)$"),
    magnitude: float = Query(1.0, ge=0.1, le=5.0)
):
    """应用外部冲击"""
    if not _fx_engine:
        return {"error": "FX engine not initialized"}
    return _fx_engine.apply_shock(shock_type, magnitude)


@router.get("/briefing")
async def get_briefing():
    """获取外汇市场简报"""
    if not _fx_engine:
        return {"error": "FX engine not initialized"}
    return _fx_engine.get_briefing()
