"""
FinanceSim Economic Router
宏观经济 API
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.dependencies import get_world_or_404
from app.models import MacroSnapshot, World
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
        raise HTTPException(status_code=503, detail="Economic engine not initialized")
    return _economic_engine.get_macro_data()


@router.get("/history")
async def get_macro_history(
    world_id: int = Query(1),
    limit: int = Query(100, le=500),
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session),
):
    """获取宏观经济历史（读 macro_snapshots 表，按 day 升序，limit 生效）。

    字段契约与旧的引擎内存历史保持兼容（gdp_growth/inflation/unemployment/
    interest_rate/money_supply/consumer_confidence/industrial_production/
    cycle_phase/cycle_position/days_since_start/simulated_date）；
    trade_balance 未落库，返回 None 而不是编造。
    """
    result = await session.execute(
        select(MacroSnapshot)
        .where(MacroSnapshot.world_id == world_id)
        .order_by(MacroSnapshot.day.asc())
        .limit(max(1, min(limit, 500)))
    )
    rows = result.scalars().all()
    return [
        {
            "gdp_growth": r.gdp_growth,
            "inflation": r.inflation,
            "unemployment": r.unemployment,
            "interest_rate": r.interest_rate,
            "money_supply": r.money_supply,
            "consumer_confidence": r.consumer_confidence,
            "industrial_production": r.industrial_production,
            "trade_balance": None,
            "cycle_position": r.cycle_position,
            "cycle_phase": r.cycle_phase,
            "day": r.day,
            "days_since_start": r.day,
            "simulated_date": r.captured_at.isoformat() if r.captured_at else None,
        }
        for r in rows
    ]


@router.post("/step")
async def step_economy(
    days: int = Query(1, ge=1, le=365),
    shock: Optional[str] = None,
    magnitude: float = Query(1.0, ge=0.1, le=5.0)
):
    """推进经济模拟"""
    if not _economic_engine:
        raise HTTPException(status_code=503, detail="Economic engine not initialized")

    # 可选：首次推进时尝试用 FRED 真实宏观数据种子合成状态。
    # 仅在 USE_EXTERNAL_DATA 且 FRED 启用时生效；失败/未启用则静默跳过。
    try:
        await _economic_engine.seed_from_external()
    except Exception as exc:  # 绝不影响主流程
        logger.warning("External macro seeding skipped/failed: %s", exc)

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
        raise HTTPException(status_code=503, detail="Central bank not initialized")
    return _central_bank.review_policy()


@router.post("/central-bank/action")
async def cb_policy_action(
    action: str = Query(..., pattern="^(cut|hike|qe)$"),
    magnitude: float = Query(0.25, ge=0.1, le=1.0)
):
    """实施货币政策"""
    if not _central_bank:
        raise HTTPException(status_code=503, detail="Central bank not initialized")
    return _central_bank.implement_policy(action, magnitude)


@router.get("/indicators")
async def get_economic_indicators():
    """获取综合经济指标"""
    if not _economic_engine:
        raise HTTPException(status_code=503, detail="Economic engine not initialized")

    state = _economic_engine.state
    return {
        "growth_indicators": {
            "gdp_growth_annual": state.gdp_growth * 100,
            "industrial_production_index": state.industrial_production,
            "consumer_confidence": state.consumer_confidence
        },
        "inflation_indicators": {
            "cpi_inflation": state.inflation * 100,
            # 加权预期（内部为小数，这里统一换算为百分数字面量，与 cpi_inflation 同口径）
            "expected_inflation": (state.inflation * 0.9 + 0.02 * 0.1) * 100
        },
        "labor_market": {
            "unemployment_rate": state.unemployment * 100,
            # 自然失业率：同为百分数字面量（5.0 表示 5%）
            "natural_rate": 5.0
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
