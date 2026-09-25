"""
FinanceSim Event Router
事件、传播和时间线 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models import Event, News
from app.schemas import EventCreate, NewsResponse
from app.engines.event_engine import EventGenerator, EventPropagation

router = APIRouter(prefix="/events", tags=["events"])

# 全局引擎实例
_event_generator = None
_event_propagation = None


def init_event_engine(gen: EventGenerator, prop: EventPropagation):
    """初始化事件引擎实例"""
    global _event_generator, _event_propagation
    _event_generator = gen
    _event_propagation = prop


@router.get("", response_model=List[NewsResponse])
async def list_news(
    world_id: int,
    limit: int = Query(50, le=200),
    importance: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """获取新闻列表"""
    query = select(News).where(News.world_id == world_id).order_by(News.created_at.desc())
    
    if importance:
        query = query.where(News.importance == importance.upper())
    
    query = query.limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/list")
async def list_events(
    world_id: int,
    limit: int = Query(50, le=200),
    event_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """获取事件列表"""
    query = (
        select(Event)
        .where(Event.world_id == world_id)
        .order_by(Event.created_at.desc())
    )
    
    if event_type:
        query = query.where(Event.type == event_type.upper())
    
    query = query.limit(limit)
    result = await session.execute(query)
    events = result.scalars().all()
    
    return [
        {
            "id": e.id,
            "type": e.type,
            "severity": e.severity,
            "title": e.title,
            "body": e.body,
            "affected_assets": e.affected_assets,
            "affected_sectors": e.affected_sectors,
            "sentiment_effect": e.sentiment_effect,
            "created_at": e.created_at.isoformat(),
            "duration_days": e.duration_days or 0
        }
        for e in events
    ]


@router.get("/timeline/{ticker}")
async def get_asset_timeline(
    ticker: str,
    world_id: int,
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_session)
):
    """获取资产事件时间线"""
    result = await session.execute(
        select(Event)
        .where(
            Event.world_id == world_id,
            Event.affected_assets.contains([ticker])
        )
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    
    return [
        {
            "id": e.id,
            "type": e.type,
            "severity": e.severity,
            "title": e.title,
            "affected_assets": e.affected_assets,
            "created_at": e.created_at.isoformat()
        }
        for e in events
    ]


@router.post("/generate")
async def generate_event(
    world_id: int,
    session: AsyncSession = Depends(get_session)
):
    """生成新事件"""
    if not _event_generator:
        raise HTTPException(status_code=500, detail="Event generator not initialized")
    
    # 获取当前世界的所有资产
    result = await session.execute(
        select(Event).__table__.c  # 这只是测试，实际需要查询 Assets
    )
    
    # 简化实现：生成一个示例事件
    event = _event_generator.generate_event(
        assets=[{"ticker": f"TEST{i}", "sector": "Technology"} for i in range(10)],
        sectors=["Technology", "Finance", "Healthcare"]
    )
    
    return event.to_dict()


@router.get("/propagation-summary")
async def get_propagation_summary(
    limit: int = Query(20, le=100)
):
    """获取事件传播摘要"""
    if not _event_propagation:
        return []
    
    return _event_propagation.get_propagation_summary(limit)
