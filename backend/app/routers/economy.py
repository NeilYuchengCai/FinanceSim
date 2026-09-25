"""
FinanceSim Economic Router
宏观经济 API
"""
from typing import List, Optional
from fastapi import APIRouter, Query
from decimal import Decimal

from app.engines import EconomicEngine, CentralBank

router = APIRouter(prefix="/economy", tags=["economy"])

# 全局引擎实例（生产环境应使用依赖注入）
_economic_engine: Optional[EconomicEngine] = None
_central_bank: Optional[CentralBank] = None


def init_economy(engine: EconomicEngine, cb: CentralBank):
    """初始化经济引擎实例"""
    global _economic_engine, _central_bank
    _economic_engine = engine
    _central_bank = cb


@router.get("/state")
async def get_macro_state():
    """获取宏观经济状态"""
    if not _economic_engine:
        return {"error": "Economic engine not initialized"}
    return _economic_engine.get_macro_data()


@router.get("/history")
async def get_macro_history(
    limit: int = Query(100, le=500)
):
    """获取宏观经济历史"""
    if not _economic_engine:
        return {"error": "Economic engine not initialized"}
    return _economic_engine.get_history(limit)


@router.post("/step")
async def step_economy(
    days: int = Query(1, ge=1, le=365),
    shock: Optional[str] = None,
    magnitude: float = Query(1.0, ge=0.1, le=5.0)
):
    """推进经济模拟"""
    if not _economic_engine:
        return {"error": "Economic engine not initialized"}
    
    shocks = {}
    if shock:
        shock_map = {
            "recession": "recession_shock",
            "stimulus": "stimulus_shock",
            "inflation_spike": "inflation_shock",
            "confidence_crisis": "confidence_shock"
        }
        if shock in shock_map:
            shocks[shock_map[shock]] = magnitude
    
    state = _economic_engine.step(days, shocks)
    return state


@router.get("/central-bank/review")
async def cb_policy_review():
    """央行货币政策审查"""
    if not _central_bank:
        return {"error": "Central bank not initialized"}
    return _central_bank.review_policy()


@router.post("/central-bank/action")
async def cb_policy_action(
    action: str = Query(..., regex="^(cut|hike|qe)$"),
    magnitude: float = Query(0.25, ge=0.1, le=1.0)
):
    """实施货币政策"""
    if not _central_bank:
        return {"error": "Central bank not initialized"}
    return _central_bank.implement_policy(action, magnitude)


@router.get("/indicators")
async def get_economic_indicators():
    """获取综合经济指标"""
    if not _economic_engine:
        return {"error": "Economic engine not initialized"}
    
    state = _economic_engine.state
    return {
        "growth_indicators": {
            "gdp_growth_annual": state.gdp_growth * 100,
            "industrial_production_index": state.industrial_production,
            "consumer_confidence": state.consumer_confidence
        },
        "inflation_indicators": {
            "cpi_inflation": state.inflation * 100,
            "expected_inflation": state.inflation * 0.9 + 0.02 * 0.1  # 加权预期
        },
        "labor_market": {
            "unemployment_rate": state.unemployment * 100,
            "natural_rate": 0.05
        },
        "monetary_policy": {
            "policy_rate": state.interest_rate * 100,
            "money_supply_growth": (state.money_supply - 1) * 100
        },
        "business_cycle": {
            "phase": state.cycle_phase,
            "position": state.cycle_position,
            "days_in_cycle": state.days_since_start
        }
    }
