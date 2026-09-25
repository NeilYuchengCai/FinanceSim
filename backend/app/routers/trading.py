"""
FinanceSim Trading Router
交易 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models import Order, Trade, Position, Asset
from app.schemas import OrderCreate, OrderResponse, TradeResponse
from app.engines.trading_engine import TradingEngine
from app.engines.portfolio_engine import PortfolioEngine

router = APIRouter(prefix="/trading", tags=["trading"])

# 全局交易引擎（实际应该按 world_id 管理）
trading_engines = {}
portfolio_engines = {}


def get_trading_engine(world_id: int) -> TradingEngine:
    if world_id not in trading_engines:
        trading_engines[world_id] = TradingEngine(world_id)
    return trading_engines[world_id]


def get_portfolio_engine(world_id: int) -> PortfolioEngine:
    if world_id not in portfolio_engines:
        # 从数据库获取初始现金
        portfolio_engines[world_id] = PortfolioEngine(world_id)
    return portfolio_engines[world_id]


@router.post("/orders", response_model=OrderResponse)
async def submit_order(
    order_data: OrderCreate,
    world_id: int,
    session: AsyncSession = Depends(get_session)
):
    """提交订单"""
    # 检查资产是否存在
    asset_result = await session.execute(
        select(Asset).where(Asset.world_id == world_id, Asset.ticker == order_data.asset_ticker)
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {order_data.asset_ticker} not found")
    
    engine = get_trading_engine(world_id)
    
    try:
        result = engine.submit_order(
            ticker=order_data.asset_ticker,
            side=order_data.side,
            order_type=order_data.type,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_price=order_data.stop_price
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    world_id: int,
):
    """取消订单"""
    engine = get_trading_engine(world_id)
    result = engine.cancel_order(order_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Order not found"))
    return result


@router.get("/orders")
async def list_orders(
    world_id: int,
    ticker: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """获取订单列表"""
    engine = get_trading_engine(world_id)
    orders = list(engine.pending_orders.values())
    
    if ticker:
        orders = [o for o in orders if o.ticker == ticker]
    if status:
        orders = [o for o in orders if o.status == status]
    
    return [{"id": o.id, "ticker": o.ticker, "side": o.side, "status": o.status} for o in orders[:limit]]


@router.get("/orderbook/{ticker}")
async def get_orderbook(
    ticker: str,
    world_id: int,
    depth: int = 10
):
    """获取订单簿"""
    engine = get_trading_engine(world_id)
    return engine.get_orderbook(ticker, depth)


@router.get("/trades")
async def list_trades(
    world_id: int,
    ticker: Optional[str] = None,
    limit: int = 100
):
    """获取成交记录"""
    engine = get_trading_engine(world_id)
    return engine.get_recent_trades(ticker, limit)


@router.get("/portfolio")
async def get_portfolio(world_id: int):
    """获取投资组合"""
    engine = get_portfolio_engine(world_id)
    return engine.get_performance()


@router.get("/portfolio/positions")
async def get_positions(world_id: int):
    """获取持仓列表"""
    engine = get_portfolio_engine(world_id)
    return engine.get_all_positions()
