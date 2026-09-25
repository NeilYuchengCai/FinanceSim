"""
FinanceSim Search Router
搜索 API
"""
from typing import List, Dict, Optional
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database import get_session
from app.models import Asset, Event, News

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    world_id: Optional[int] = None,
    limit: int = Query(20, le=50),
    session: AsyncSession = Depends(get_session)
):
    """全局搜索"""
    results = {
        "assets": [],
        "events": [],
        "news": []
    }
    
    query = q.upper()
    
    # 搜索资产
    asset_query = select(Asset).where(
        or_(
            Asset.ticker.ilike(f"%{query}%"),
            Asset.name.ilike(f"%{query}%")
        )
    )
    if world_id:
        asset_query = asset_query.where(Asset.world_id == world_id)
    asset_result = await session.execute(asset_query.limit(limit))
    assets = asset_result.scalars().all()
    results["assets"] = [
        {
            "type": "asset",
            "ticker": a.ticker,
            "name": a.name,
            "sector": a.sector
        }
        for a in assets
    ]
    
    # 搜索事件
    event_query = select(Event).where(
        or_(
            Event.title.ilike(f"%{query}%"),
            Event.type.ilike(f"%{query}%")
        )
    )
    if world_id:
        event_query = event_query.where(Event.world_id == world_id)
    event_result = await session.execute(event_query.limit(limit))
    events = event_result.scalars().all()
    results["events"] = [
        {
            "type": "event",
            "id": e.id,
            "title": e.title,
            "type_name": e.type
        }
        for e in events
    ]
    
    # 搜索新闻
    news_query = select(News).where(
        News.headline.ilike(f"%{query}%")
    )
    if world_id:
        news_query = news_query.where(News.world_id == world_id)
    news_result = await session.execute(news_query.limit(limit))
    news = news_result.scalars().all()
    results["news"] = [
        {
            "type": "news",
            "id": n.id,
            "headline": n.headline,
            "importance": n.importance
        }
        for n in news
    ]
    
    return results
