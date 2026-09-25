"""
FinanceSim Commodity Router
商品市场 API
"""
from typing import Optional
from fastapi import APIRouter, Query

from app.engines import CommodityEngine

router = APIRouter(prefix="/commodities", tags=["commodities"])

_engine: Optional[CommodityEngine] = None


def init_commodity_engine(engine: CommodityEngine):
    global _engine
    _engine = engine


@router.get("")
async def list_commodities():
    if not _engine:
        return {"error": "Commodity engine not initialized"}
    return _engine.get_all_commodities()


@router.get("/summary")
async def get_summary():
    if not _engine:
        return {"error": "Commodity engine not initialized"}
    return _engine.get_market_summary()


@router.get("/{ticker}")
async def get_commodity(ticker: str):
    if not _engine:
        return {"error": "Commodity engine not initialized"}
    result = _engine.get_commodity(ticker)
    if not result:
        return {"error": f"Commodity {ticker} not found"}
    return result


@router.get("/{ticker}/history")
async def get_history(ticker: str, limit: int = Query(100, le=500)):
    if not _engine:
        return {"error": "Commodity engine not initialized"}
    return _engine.get_price_history(ticker, limit)


@router.post("/step")
async def step_commodities(
    days: int = Query(1, ge=1, le=365),
    volatility_mult: float = Query(1.0, ge=0.1, le=5.0)
):
    if not _engine:
        return {"error": "Commodity engine not initialized"}
    results = {}
    for _ in range(days):
        results = _engine.step(volatility_mult)
    return results


@router.post("/shock")
async def apply_shock(
    shock_type: str = Query(..., pattern="^(geopolitical|weather|demand_shock|supply_disruption|dollar_strength)$"),
    magnitude: float = Query(1.0, ge=0.1, le=5.0)
):
    if not _engine:
        return {"error": "Commodity engine not initialized"}
    return _engine.apply_shock(shock_type, magnitude)
