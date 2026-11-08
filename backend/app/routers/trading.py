"""
FinanceSim Trading Router
交易 API
"""
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.dependencies import get_world_or_404
from app.models import Order, Trade, Position, Asset, World, UserEconomy
from app.schemas import OrderCreate, OrderResponse, TradeResponse
from app.engines.trading_engine import TradingEngine
from app.engines.portfolio_engine import PortfolioEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])

# 全局交易引擎（实际应该按 world_id 管理）
trading_engines = {}
portfolio_engines = {}

# 订单列表默认过滤口径
OPEN_STATUSES = ("PENDING", "PARTIAL")
ORDERS_LIMIT_CAP = 200
TRADES_LIMIT_CAP = 500


def _jsonable(value):
    """HTTP 响应边界：把引擎/DB 读回的 Decimal 转成 JSON 数字。

    铁律②要求落库路径保持 Decimal；但接口层直接返回 Decimal 时，
    FastAPI 的 jsonable_encoder 虽能处理，参与前端 float 运算或某些序列化
    分支仍可能踩类型混用。这里只在**读接口边界**统一转换，
    不触碰任何写入 DB 的路径。
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def get_trading_engine(world_id: int) -> TradingEngine:
    if world_id not in trading_engines:
        trading_engines[world_id] = TradingEngine(world_id)
    return trading_engines[world_id]


async def get_portfolio_engine(world_id: int, session: AsyncSession) -> PortfolioEngine:
    """获取（或按需从数据库恢复）投资组合引擎。

    首次创建时：
    - 初始现金取 World.starting_capital（不再硬编码 100000）；
    - 若 user_economy / positions 表已有数据（服务重启场景），
      则恢复真实现金与持仓，保证交易状态跨重启保持。
    """
    if world_id not in portfolio_engines:
        world = await session.get(World, world_id)
        initial_cash = Decimal(str(getattr(world, "starting_capital", None) or 100000.0))
        engine = PortfolioEngine(world_id, initial_cash=initial_cash)
        try:
            rows = (await session.execute(
                select(Position.quantity, Position.avg_price, Position.last_price, Asset.ticker)
                .join(Asset, Asset.id == Position.asset_id)
                .where(Position.world_id == world_id)
            )).all()
            positions = [
                {"ticker": r[3], "quantity": r[0], "avg_price": r[1], "last_price": r[2]}
                for r in rows
            ]
            economy = (await session.execute(
                select(UserEconomy).where(UserEconomy.world_id == world_id)
            )).scalar_one_or_none()
            cash = Decimal(str(economy.cash)) if economy is not None else initial_cash
            engine.restore_from_db(cash, positions)
        except Exception as e:
            logger.warning(f"Failed to restore portfolio for world {world_id}: {e}")
        portfolio_engines[world_id] = engine
    return portfolio_engines[world_id]


async def _persist_trading_state(
    session: AsyncSession,
    world: World,
    asset: Asset,
    result: Dict,
    portfolio: PortfolioEngine,
) -> None:
    """把一次成交的订单/成交/持仓/现金落库（路由层持久化，引擎保持纯计算）。

    任何落库失败只向上抛给调用方记录日志，不打断已完成的成交响应。
    """
    order_row = Order(
        id=result["order_id"],
        world_id=world.id,
        asset_id=asset.id,
        side=result["side"],
        type=result["type"],
        quantity=result["quantity"],
        price=result.get("price"),
        stop_price=result.get("stop_price"),
        filled_quantity=result.get("filled_quantity") or 0,
        avg_fill_price=result.get("avg_fill_price"),
        status=result["status"],
        created_by=result.get("created_by") or "USER",
        created_at=datetime.now(),
    )
    session.add(order_row)

    for tr in result.get("trades") or []:
        ts = tr.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = None
        # 无条件落库：timestamp 本来就是 datetime 的正常路径也必须写成交记录。
        # 此前误缩进到 `if isinstance(ts, str)` 内，导致绝大多数成交完全不落库。
        session.add(Trade(
            id=tr.get("id") or str(uuid.uuid4()),
            world_id=world.id,
            asset_id=asset.id,
            order_id_buy=tr.get("order_id_buy"),
            order_id_sell=tr.get("order_id_sell"),
            # 铁律②：金额/价格直接以 Decimal 落地，禁止 float() 截断核心金额
            price=Decimal(str(tr.get("price") or 0)),
            quantity=Decimal(str(tr.get("quantity") or 0)),
            direction=tr.get("direction") or result["side"],
            timestamp=ts or datetime.now(),
            world_day=world.current_day,
        ))

    # 持仓 upsert（本订单只影响单一标的；清仓则删除该行）
    pos = portfolio.get_position(asset.ticker)
    existing = (await session.execute(
        select(Position).where(Position.world_id == world.id, Position.asset_id == asset.id)
    )).scalar_one_or_none()
    if pos is None or pos["quantity"] <= 0:
        if existing is not None:
            await session.delete(existing)
    elif existing is None:
        session.add(Position(
            id=str(uuid.uuid4()),
            world_id=world.id,
            asset_id=asset.id,
            quantity=float(pos["quantity"]),
            avg_price=float(pos["avg_price"]),
            last_price=float(pos["last_price"]),
            unrealized_pnl=float(pos["unrealized_pnl"]),
        ))
    else:
        existing.quantity = float(pos["quantity"])
        existing.avg_price = float(pos["avg_price"])
        existing.last_price = float(pos["last_price"])
        existing.unrealized_pnl = float(pos["unrealized_pnl"])

    # 现金持久化到 user_economy（重启后现金不从初始值重置）
    economy = (await session.execute(
        select(UserEconomy).where(UserEconomy.world_id == world.id)
    )).scalar_one_or_none()
    if economy is None:
        # 铁律②：现金直接以 Decimal 落地，禁止 float() 截断
        session.add(UserEconomy(world_id=world.id, cash=portfolio.cash))
    else:
        economy.cash = portfolio.cash

    await session.commit()


@router.post("/orders")
async def submit_order(
    order_data: OrderCreate,
    world_id: int,
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session)
):
    """提交订单：撮合 + 同步用户投资组合（现金/持仓）+ 落库。"""
    # 检查资产是否存在
    asset_result = await session.execute(
        select(Asset).where(Asset.world_id == world_id, Asset.ticker == order_data.asset_ticker)
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {order_data.asset_ticker} not found")

    side = order_data.side.upper()
    otype = order_data.type.upper()
    portfolio = await get_portfolio_engine(world_id, session)

    # 预检：资金 / 持仓是否足够，避免成交后才发现无法入账造成状态不一致
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
    except ValueError as e:
        # 业务错误（资金/持仓/参数）明确归为 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 未知异常：记录服务端日志，返回通用 500，不把 bug 伪装成用户错误
        logger.exception(f"submit_order failed for world {world_id}: {e}")
        raise HTTPException(status_code=500, detail="订单提交失败，请稍后重试")

    # 同步用户投资组合（仅对成交部分入账）：金额全程 Decimal，避免 float 截断
    if result.get("trades"):
        agg: Dict[str, Dict[str, Decimal]] = defaultdict(
            lambda: {"qty": Decimal("0"), "cost": Decimal("0")}
        )
        for tr in result["trades"]:
            tk = tr.get("ticker")
            q = Decimal(str(tr.get("quantity", 0) or 0))
            p = Decimal(str(tr.get("price", 0) or 0))
            if tk and q:
                agg[tk]["qty"] += q
                agg[tk]["cost"] += q * p
        try:
            for tk, info in agg.items():
                avg = info["cost"] / info["qty"] if info["qty"] else Decimal("0")
                if side == "BUY":
                    portfolio.buy(tk, info["qty"], avg)
                elif side == "SELL":
                    portfolio.sell(tk, info["qty"], avg)
        except ValueError as pe:
            raise HTTPException(status_code=400, detail=f"组合更新失败：{pe}")

    # 落库（订单/成交/持仓/现金）：失败只记录，不影响已完成的成交响应
    try:
        await _persist_trading_state(session, world, asset, result, portfolio)
    except Exception as e:
        logger.exception(f"Failed to persist trading state for world {world_id}: {e}")
        try:
            await session.rollback()
        except Exception:
            pass

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
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session),
):
    """取消订单"""
    engine = get_trading_engine(world_id)
    result = engine.cancel_order(order_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Order not found"))
    # 同步落库状态
    try:
        order_row = (await session.execute(
            select(Order).where(Order.id == order_id, Order.world_id == world_id)
        )).scalar_one_or_none()
        if order_row is not None and order_row.status not in ("FILLED", "CANCELLED"):
            order_row.status = "CANCELLED"
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to persist cancel for order {order_id}: {e}")
    return result


@router.get("/orders")
async def list_orders(
    world_id: int,
    world: World = Depends(get_world_or_404),
    ticker: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """获取订单列表。

    默认只返回未成交订单（PENDING/PARTIAL），排除 AI 交易员（BOT: 前缀）订单；
    显式传 status 时才检索已完成订单（成交记录请走 /trading/trades）。
    """
    engine = get_trading_engine(world_id)
    orders = list(engine.pending_orders.values())
    if status:
        # 显式查询历史状态时才合并已完成订单
        orders += list(engine.completed_orders.values())

    if ticker:
        orders = [o for o in orders if o.ticker == ticker]
    if status:
        orders = [o for o in orders if o.status == status.upper()]
    else:
        orders = [o for o in orders if o.status in OPEN_STATUSES]
    # 默认排除机器人订单，避免用户订单列表被 AI 交易员刷屏
    orders = [o for o in orders if not o.created_by.startswith("BOT:")]

    limit = max(1, min(limit, ORDERS_LIMIT_CAP))
    return [
        {
            "id": o.id,
            "ticker": o.ticker,
            "side": o.side,
            "type": o.type,
            "status": o.status,
            "quantity": float(o.original_quantity),
            "filled_quantity": float(o.filled_quantity),
            "price": float(o.price) if o.price else None,
            "created_by": o.created_by,
            "created_at": o.created_at.isoformat(),
        }
        for o in orders[:limit]
    ]


@router.get("/orderbook/{ticker}")
async def get_orderbook(
    ticker: str,
    world_id: int,
    world: World = Depends(get_world_or_404),
    depth: int = 10
):
    """获取订单簿"""
    engine = get_trading_engine(world_id)
    return engine.get_orderbook(ticker, depth)


@router.get("/trades")
async def list_trades(
    world_id: int,
    world: World = Depends(get_world_or_404),
    ticker: Optional[str] = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """获取成交记录。

    DB 成交（用户订单，重启后仍可查）与引擎内存中尚未落库的成交
    （AI 交易员走引擎直接撮合）按 id 去重合并，保证列表完整且跨重启保持。
    """
    cap = max(1, min(limit, TRADES_LIMIT_CAP))
    query = (
        select(Trade, Asset.ticker)
        .join(Asset, Asset.id == Trade.asset_id)
        .where(Trade.world_id == world_id)
    )
    if ticker:
        query = query.where(Asset.ticker == ticker)
    query = query.order_by(Trade.timestamp.desc()).limit(cap)
    rows = (await session.execute(query)).all()

    seen = set()
    out = []
    for t, tk in rows:
        seen.add(t.id)
        out.append({
            "id": t.id,
            "ticker": tk,
            "price": t.price,
            "quantity": t.quantity,
            "direction": t.direction,
            "timestamp": t.timestamp.isoformat() if t.timestamp else None,
            "order_id_buy": t.order_id_buy,
            "order_id_sell": t.order_id_sell,
            "buyer_order_id": t.order_id_buy,
            "seller_order_id": t.order_id_sell,
            "world_id": t.world_id,
            "world_day": t.world_day,
        })

    # 合并内存中未落库的成交（机器人订单），按时间倒序补齐
    engine = get_trading_engine(world_id)
    for tr in reversed(engine.trades):
        if len(out) >= cap:
            break
        tr_id = tr.get("id")
        if tr_id in seen:
            continue
        if ticker and tr.get("ticker") != ticker:
            continue
        seen.add(tr_id)
        ts = tr.get("timestamp")
        out.append({
            "id": tr_id,
            "ticker": tr.get("ticker"),
            "price": tr.get("price"),
            "quantity": tr.get("quantity"),
            "direction": tr.get("direction") or ("BUY" if tr.get("buyer_order_id") else "SELL"),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else ts,
            "order_id_buy": tr.get("order_id_buy"),
            "order_id_sell": tr.get("order_id_sell"),
            "buyer_order_id": tr.get("buyer_order_id"),
            "seller_order_id": tr.get("seller_order_id"),
            "world_id": tr.get("world_id"),
            "world_day": None,
        })

    out.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    # Trade.price/quantity 现为 Numeric -> Decimal，读接口边界统一转 JSON 数字
    return _jsonable(out[:cap])


@router.get("/portfolio")
async def get_portfolio(
    world_id: int,
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session),
):
    """获取投资组合"""
    engine = await get_portfolio_engine(world_id, session)
    return _jsonable(engine.get_performance())


@router.get("/portfolio/positions")
async def get_positions(
    world_id: int,
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session),
):
    """获取持仓列表"""
    engine = await get_portfolio_engine(world_id, session)
    return _jsonable(engine.get_all_positions())
