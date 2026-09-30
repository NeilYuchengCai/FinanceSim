"""
FinanceSim Trading Router
交易 API
"""
from collections import defaultdict
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


@router.post("/orders")
async def submit_order(
    order_data: OrderCreate,
    world_id: int,
    session: AsyncSession = Depends(get_session)
):
    """提交订单：撮合 + 同步用户投资组合（现金/持仓）。"""
    # 检查资产是否存在
    asset_result = await session.execute(
        select(Asset).where(Asset.world_id == world_id, Asset.ticker == order_data.asset_ticker)
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {order_data.asset_ticker} not found")

    side = order_data.side.upper()
    otype = order_data.type.upper()
    portfolio = get_portfolio_engine(world_id)

    # 预检：资金 / 持仓是否足够，避免成交后才发现无法入账造成状态不一致
    from decimal import Decimal
    est_price = order_data.price if order_data.price is not None else _mid_price(order_data.asset_ticker)
    if side == "BUY" and est_price:
        need = Decimal(str(est_price)) * Decimal(str(order_data.quantity))
        if need > portfolio.cash + Decimal("1e-6"):
            raise HTTPException(
                status_code=400,
                detail=f"资金不足：约需 {need:.2f}，可用 {portfolio.cash:.2f}",
            )
    if side == "SELL":
        pos = portfolio.get_position(order_data.asset_ticker)
        have = float(pos["quantity"]) if pos else 0.0
        if float(order_data.quantity) > have + 1e-9:
            raise HTTPException(
                status_code=400,
                detail=f"持仓不足：需卖出 {order_data.quantity}，当前持有 {have}",
            )

    engine = get_trading_engine(world_id)
    try:
        result = engine.submit_order(
            ticker=order_data.asset_ticker,
            side=side,
            order_type=otype,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_price=order_data.stop_price,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 同步用户投资组合（仅对成交部分入账）
    if result.get("trades"):
        agg: Dict[str, Dict[str, float]] = defaultdict(lambda: {"qty": 0.0, "cost": 0.0})
        for tr in result["trades"]:
            tk = tr.get("ticker")
            q = float(tr.get("quantity", 0) or 0)
            p = float(tr.get("price", 0) or 0)
            if tk and q:
                agg[tk]["qty"] += q
                agg[tk]["cost"] += q * p
        try:
            for tk, info in agg.items():
                avg = info["cost"] / info["qty"] if info["qty"] else 0.0
                if side == "BUY":
                    portfolio.buy(tk, info["qty"], avg)
                elif side == "SELL":
                    portfolio.sell(tk, info["qty"], avg)
        except Exception as pe:
            raise HTTPException(status_code=400, detail=f"组合更新失败：{pe}")

    return result


def _mid_price(ticker: str) -> Optional[float]:
    """从实时行情流取当前市场价，用于下单前的资金/持仓预检。"""
    try:
        from app.services.market_stream import get_market_stream
        st = get_market_stream()._assets.get(ticker)
        if st:
            return float(st.price)
    except Exception:
        pass
    return None


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
