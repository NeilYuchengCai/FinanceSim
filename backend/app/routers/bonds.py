"""
FinanceSim Bond Router
债券市场 API
"""
from typing import List, Optional
from fastapi import APIRouter, Query

from app.engines import BondEngine

router = APIRouter(prefix="/bonds", tags=["bonds"])

_bond_engine: Optional[BondEngine] = None


def init_bond_engine(engine: BondEngine):
    """初始化债券引擎实例"""
    global _bond_engine
    _bond_engine = engine


@router.get("")
async def list_bonds(
    bond_type: Optional[str] = Query(None),
    rating: Optional[str] = Query(None),
    limit: int = Query(50, le=100)
):
    """获取债券列表"""
    if not _bond_engine:
        return {"error": "Bond engine not initialized"}
    
    bonds = _bond_engine.get_all_bonds()
    
    if bond_type:
        bonds = [b for b in bonds if b["type"] == bond_type.upper()]
    if rating:
        bonds = [b for b in bonds if b["credit_rating"] == rating.upper()]
    
    return bonds[:limit]


@router.get("/{ticker}")
async def get_bond(ticker: str):
    """获取单个债券详情"""
    if not _bond_engine:
        return {"error": "Bond engine not initialized"}
    
    bond = _bond_engine.get_bond(ticker)
    if not bond:
        return {"error": f"Bond {ticker} not found"}
    
    return bond.to_dict()


@router.get("/yield-curve")
async def get_yield_curve():
    """获取收益率曲线"""
    if not _bond_engine:
        return {"error": "Bond engine not initialized"}
    
    return _bond_engine.get_yield_curve()


@router.post("/step")
async def step_bonds(
    days: int = Query(1, ge=1, le=365),
    shock: Optional[str] = None,
    magnitude: float = Query(1.0, ge=0.1, le=5.0)
):
    """推进债券市场"""
    if not _bond_engine:
        return {"error": "Bond engine not initialized"}
    
    shocks = {}
    if shock:
        shock_map = {
            "rate_hike": "rate_hike",
            "rate_cut": "rate_cut",
            "credit_spread_widen": "credit_spread_widen"
        }
        if shock in shock_map:
            shocks[shock_map[shock]] = magnitude
    
    _bond_engine.step(days, shocks)
    
    return {
        "yield_curve": _bond_engine.get_yield_curve(),
        "sample_bonds": {t: b.to_dict() for t, b in list(_bond_engine.bonds.items())[:5]}
    }


@router.post("/{ticker}/credit-event")
async def apply_credit_event(
    ticker: str,
    rating_change: str = Query(..., regex="^(AAA|AA|A|BBB|BB|B|CCC)$")
):
    """应用信用事件"""
    if not _bond_engine:
        return {"error": "Bond engine not initialized"}
    
    _bond_engine.apply_credit_event(ticker, rating_change)
    return _bond_engine.get_bond(ticker).to_dict()


@router.get("/analytics/{ticker}")
async def bond_analytics(
    ticker: str,
    yield_change: float = Query(0.01, ge=-0.1, le=0.1)
):
    """债券分析 - 计算收益率变化影响"""
    if not _bond_engine:
        return {"error": "Bond engine not initialized"}
    
    bond = _bond_engine.get_bond(ticker)
    if not bond:
        return {"error": f"Bond {ticker} not found"}
    
    impact = bond.get_change(yield_change)
    
    return {
        "ticker": ticker,
        "current_price": bond.price,
        "current_yield": bond.yield_to_maturity,
        "duration": bond.duration,
        "convexity": bond.convexity,
        "spread": bond.spread,
        "yield_change_bps": yield_change * 10000,
        "price_impact": impact
    }
