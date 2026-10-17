"""
FinanceSim Commodity Router
商品市场 API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.engines import CommodityEngine

router = APIRouter(prefix="/commodities", tags=["commodities"])

_engine: Optional[CommodityEngine] = None


def init_commodity_engine(engine: CommodityEngine):
    """初始化商品引擎实例"""
    global _engine
    _engine = engine


def _require_engine() -> CommodityEngine:
    if not _engine:
        raise HTTPException(status_code=503, detail="Commodity engine not initialized")
    return _engine


@router.get("")
async def list_commodities():
    engine = _require_engine()
    return engine.get_all_commodities()


@router.get("/summary")
async def get_summary():
    engine = _require_engine()
    return engine.get_market_summary()


@router.get("/{ticker}")
async def get_commodity(ticker: str):
    engine = _require_engine()
    result = engine.get_commodity(ticker)
    if not result:
        raise HTTPException(status_code=404, detail=f"Commodity {ticker} not found")
    return result


@router.get("/{ticker}/history")
async def get_history(ticker: str, limit: int = Query(100, le=500)):
    engine = _require_engine()
    history = engine.get_price_history(ticker, limit)
    if not history:
        raise HTTPException(status_code=404, detail=f"Commodity {ticker} not found")
    return history


@router.post("/step")
async def step_commodities(
    days: int = Query(1, ge=1, le=365),
    volatility_mult: float = Query(1.0, ge=0.1, le=5.0)
):
    engine = _require_engine()
    results = {}
    for _ in range(days):
        results = engine.step(volatility_mult)
    return results


@router.post("/shock")
async def apply_shock(
    shock_type: str = Query(..., pattern="^(geopolitical|weather|demand_shock|supply_disruption|dollar_strength)$"),
    magnitude: float = Query(1.0, ge=0.1, le=5.0)
):
    engine = _require_engine()
    return engine.apply_shock(shock_type, magnitude)
