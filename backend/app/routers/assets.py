"""
FinanceSim Asset Router
资产管理 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_session
from app.models import Asset, PriceHistory
from app.schemas import AssetCreate, AssetResponse, PriceBar

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetResponse)
async def create_asset(
    asset_data: AssetCreate, 
    world_id: int,
    session: AsyncSession = Depends(get_session)
):
    """创建资产"""
    # 检查是否已存在
    result = await session.execute(
        select(Asset).where(Asset.world_id == world_id, Asset.ticker == asset_data.ticker)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ticker already exists")
    
    asset = Asset(
        world_id=world_id,
        ticker=asset_data.ticker,
        type=asset_data.type,
        name=asset_data.name,
        exchange=asset_data.exchange,
        sector=asset_data.sector,
        industry=asset_data.industry,
        currency=asset_data.currency,
        market_cap=asset_data.market_cap,
        beta=asset_data.beta,
        volatility=asset_data.volatility,
        fundamentals=asset_data.fundamentals
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


@router.get("", response_model=List[AssetResponse])
async def list_assets(
    world_id: int,
    asset_type: Optional[str] = Query(None, alias="asset_type"),
    # 兼容前端早期写法 ?type=EQUITY：缺这个别名时 type 过滤会被静默忽略，
    # 股票页会把债券/外汇/ETF 一起渲染出来。
    asset_type_alt: Optional[str] = Query(None, alias="type"),
    sector: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=2000),
    # 附带真实涨跌幅（最近两根 K 线）。默认关闭以免列表接口变慢；
    # 股票/外汇等需要展示涨跌的页面显式传 with_change=1。
    with_change: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    """获取资产列表"""
    effective_type = asset_type or asset_type_alt

    query = select(Asset).where(Asset.world_id == world_id)
    
    if effective_type:
        query = query.where(Asset.type == effective_type.upper())
    if sector:
        query = query.where(Asset.sector == sector)
    
    query = query.order_by(Asset.ticker)
    if limit:
        query = query.limit(limit)
    result = await session.execute(query)
    assets = result.scalars().all()

    if not with_change:
        return assets

    stats = await _latest_stats(session, [a.id for a in assets])
    out = []
    for a in assets:
        item = AssetResponse.model_validate(a)
        prev_close, change_pct, last_volume = stats.get(a.id, (None, None, None))
        item.prev_close = prev_close
        item.change_pct = change_pct
        item.last_volume = last_volume
        out.append(item)
    return out


async def _latest_stats(session: AsyncSession, asset_ids: List[int]) -> dict:
    """批量取每个资产最近两根 K 线，算出涨跌幅与最新成交量。

    用窗口函数一次查完，避免 N+1。
    返回 {asset_id: (prev_close, change_pct, last_volume)}。
    """
    ids = [int(i) for i in asset_ids if i is not None]
    if not ids:
        return {}

    # asset_id 是整数主键，已强制 int 转换，不存在注入风险
    rows = (
        await session.execute(
            text(
                "SELECT asset_id, rn, close, volume FROM ("
                "  SELECT asset_id, close, volume,"
                "         ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY timestamp DESC) AS rn"
                f"  FROM price_history WHERE asset_id IN ({','.join(str(i) for i in ids)})"
                ") WHERE rn <= 2"
            )
        )
    ).fetchall()

    by_asset: dict = {}
    for asset_id, rn, close, volume in rows:
        by_asset.setdefault(int(asset_id), {})[int(rn)] = (
            float(close) if close is not None else None,
            float(volume) if volume is not None else None,
        )

    out = {}
    for asset_id, bars in by_asset.items():
        cur, last_volume = bars.get(1, (None, None))
        prev = bars.get(2, (None, None))[0]
        if cur is None:
            continue
        if prev in (None, 0):
            out[asset_id] = (prev, 0.0, last_volume)
        else:
            out[asset_id] = (prev, (cur - prev) / prev * 100.0, last_volume)
    return out


# NOTE: /price-history 必须声明在 /{ticker} 之前，否则会被 "/{ticker}" 路径参数拦截。
@router.get("/price-history")
async def get_price_history_by_ticker(
    ticker: str,
    world_id: int = Query(1),
    limit: int = Query(50, le=1000),
    session: AsyncSession = Depends(get_session)
):
    """按 ticker 获取价格历史（前端 Timeline 图表使用）"""
    asset_result = await session.execute(
        select(Asset.id).where(Asset.world_id == world_id, Asset.ticker == ticker)
    )
    asset_id = asset_result.scalar_one_or_none()
    if not asset_id:
        return []

    result = await session.execute(
        select(PriceHistory)
        .where(PriceHistory.asset_id == asset_id)
        .order_by(PriceHistory.timestamp.desc())
        .limit(limit)
    )
    prices = list(reversed(result.scalars().all()))

    return [
        {
            "time": p.timestamp.isoformat(),
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
        }
        for p in prices
    ]


@router.get("/{ticker}", response_model=AssetResponse)
async def get_asset(
    ticker: str,
    world_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取单个资产"""
    result = await session.execute(
        select(Asset).where(Asset.world_id == world_id, Asset.ticker == ticker)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{ticker}/price")
async def restore_asset_price(
    ticker: str,
    price: float,
    world_id: int = Query(1),
    session: AsyncSession = Depends(get_session)
):
    """恢复指定资产的当前价格（存档加载用）。"""
    from app.services.market_stream import get_market_stream
    stream = get_market_stream()
    ok = stream.set_price(ticker, price)
    if not ok:
        raise HTTPException(status_code=404, detail="Asset not in market stream")
    # 同步落库，保证后续 persist 不会覆盖
    result = await session.execute(
        select(Asset).where(Asset.world_id == world_id, Asset.ticker == ticker)
    )
    asset = result.scalar_one_or_none()
    if asset is not None:
        asset.current_price = price
        await session.commit()
    return {"ticker": ticker, "price": price, "restored": True}


@router.get("/{ticker}/history", response_model=List[PriceBar])
async def get_price_history(
    ticker: str,
    world_id: int,
    limit: int = Query(100, le=1000),
    session: AsyncSession = Depends(get_session)
):
    """获取价格历史"""
    # 先获取资产 ID
    asset_result = await session.execute(
        select(Asset.id).where(Asset.world_id == world_id, Asset.ticker == ticker)
    )
    asset_id = asset_result.scalar_one_or_none()
    if not asset_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # 获取价格历史
    result = await session.execute(
        select(PriceHistory)
        .where(PriceHistory.asset_id == asset_id)
        .order_by(PriceHistory.timestamp.desc())
        .limit(limit)
    )
    prices = result.scalars().all()
    
    # 反转顺序（从旧到新）
    return list(reversed(prices))
