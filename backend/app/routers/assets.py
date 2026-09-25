"""
FinanceSim Asset Router
资产管理 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
    asset_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """获取资产列表"""
    query = select(Asset).where(Asset.world_id == world_id)
    
    if asset_type:
        query = query.where(Asset.type == asset_type.upper())
    if sector:
        query = query.where(Asset.sector == sector)
    
    query = query.order_by(Asset.ticker)
    result = await session.execute(query)
    return result.scalars().all()


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
