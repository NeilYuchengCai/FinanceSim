"""
FinanceSim FX Router
外汇市场 API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.engines import FXEngine

router = APIRouter(prefix="/fx", tags=["fx"])

_fx_engine: Optional[FXEngine] = None


def init_fx_engine(engine: FXEngine):
    """初始化外汇引擎实例"""
    global _fx_engine
    _fx_engine = engine


def _require_engine() -> FXEngine:
    if not _fx_engine:
        raise HTTPException(status_code=503, detail="FX engine not initialized")
    return _fx_engine


@router.get("/pairs")
async def list_pairs():
    """获取所有货币对"""
    engine = _require_engine()
    return engine.get_all_pairs()


@router.get("/pair/{ticker:path}/history")
async def get_history(
    ticker: str,
    limit: int = Query(100, le=500)
):
    """获取历史价格。

    ticker 用 :path 转换器接收含 "/" 的货币对 key（如 EUR/USD）；
    本路由必须先于 /pair/{ticker:path} 声明，否则会被详情路由捕获。
    """
    engine = _require_engine()
    return engine.get_price_history(ticker, limit)


@router.get("/pair/{ticker:path}")
async def get_pair(ticker: str):
    """获取单个货币对详情。

    路径参数不能包含 "/"，而引擎 key 是 "EUR/USD"；这里用 :path 转换器
    接收完整 key，并用引擎的 normalize_ticker 归一化
    （EURUSD / eur-usd -> EUR/USD）后再查询。
    """
    engine = _require_engine()

    pair = engine.get_pair(ticker)
    if not pair:
        raise HTTPException(status_code=404, detail=f"Pair {ticker} not found")
    return pair.to_dict()


@router.post("/step")
async def step_fx(
    days: int = Query(1, ge=1, le=365),
    volatility_mult: float = Query(1.0, ge=0.1, le=5.0)
):
    """推进外汇市场"""
    engine = _require_engine()

    results = {}
    for _ in range(days):
        results = engine.step(volatility_mult)

    return results


@router.post("/shock")
async def apply_shock(
    shock_type: str = Query(..., pattern="^(central_bank|crisis|trade_war|pandemic)$"),
    magnitude: float = Query(1.0, ge=0.1, le=5.0)
):
    """应用外部冲击"""
    engine = _require_engine()
    return engine.apply_shock(shock_type, magnitude)


@router.get("/briefing")
async def get_briefing():
    """获取外汇市场简报"""
    engine = _require_engine()
    return engine.get_briefing()
