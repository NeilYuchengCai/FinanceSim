"""
FinanceSim Event Router
事件、传播和时间线 API
"""
import logging
import math
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_session
from app.dependencies import get_world_or_404
from app.models import Event, News, Asset, World
from app.schemas import EventCreate, NewsResponse
from app.engines.event_engine import EventGenerator, EventPropagation, Event as SimEvent
from app.core.datasource import DataSource
from app.services.market_stream import (
    get_market_stream,
    SECONDS_PER_YEAR,
    TICK_VOL_SCALE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

# 全局引擎实例
_event_generator = None
_event_propagation = None

# ---------------------------------------------------------------- 价格冲击参数
# 单次事件冲击占价格比例的上限：封顶 ±5%，防止黑天鹅一戳到底
MAX_EVENT_SHOCK_PCT = 0.05
# propagate 输出的 impact（severity*sentiment 量级 ±1）到价格冲击的基础换算系数
IMPACT_TO_PRICE = 0.12
# 波动率差异化：以年化 25% 的普通股票为基准 1.0，缩放范围 [0.5, 2.0]
# 注意：此处与 market_stream 的 state.sigma 采用同一"每模拟秒年化折算"口径，
# 因此 vol_ratio = 资产波动率 / 0.25，与倍速无关、跨速度一致。
_REFERENCE_SIGMA = (
    0.25 / math.sqrt(SECONDS_PER_YEAR) * TICK_VOL_SCALE
)
VOL_SCALE_RANGE = (0.5, 2.0)
# 事件类型差异化：危机类冲击最大，宏观类居中，公司类最温和
EVENT_TYPE_SHOCK_SCALE = {
    "liquidity_crisis": 1.5,
    "banking_crisis": 1.5,
    "black_swan": 1.5,
    "geopolitical": 1.0,
    "central_bank": 1.0,
    "inflation_shock": 1.0,
    "employment_shock": 1.0,
}
DEFAULT_TYPE_SHOCK_SCALE = 0.7  # COMPANY 类事件


def apply_event_price_shocks(event: SimEvent, assets: List[Dict]) -> List[Dict]:
    """把事件传播影响封顶后按资产波动率/事件类型差异化施加到行情。

    返回实际施加的明细 [{ticker, level, sector, raw_impact, applied_pct}]，
    供日志核对；传播引擎或行情流不可用时返回空列表。
    """
    if _event_propagation is None:
        return []
    stream = get_market_stream()
    if stream is None:
        return []

    impacts = _event_propagation.propagate(event, assets)
    type_scale = EVENT_TYPE_SHOCK_SCALE.get(event.type, DEFAULT_TYPE_SHOCK_SCALE)

    applied: List[Dict] = []
    for imp in impacts:
        ticker = imp.get("ticker")
        if not ticker or ticker == "MACRO":
            continue  # 宏观影响不直接映射到单个行情标的
        raw = float(imp.get("impact") or 0.0)
        if raw == 0.0:
            continue
        state = stream._assets.get(ticker)
        if state is None:
            continue

        # 1) 基础换算并封顶 ±5%
        base = max(-MAX_EVENT_SHOCK_PCT, min(MAX_EVENT_SHOCK_PCT, raw * IMPACT_TO_PRICE))
        # 2) 按资产波动率差异化：高波动资产对同一事件反应更大
        vol_ratio = state.sigma / _REFERENCE_SIGMA if _REFERENCE_SIGMA > 0 else 1.0
        vol_scale = max(VOL_SCALE_RANGE[0], min(VOL_SCALE_RANGE[1], vol_ratio))
        # 3) 按事件类型差异化，并再次封顶，保证任何组合都不超过 ±5%
        pct = max(-MAX_EVENT_SHOCK_PCT,
                  min(MAX_EVENT_SHOCK_PCT, base * vol_scale * type_scale))
        if pct == 0.0:
            continue
        stream.apply_shock(ticker, pct)
        applied.append({
            "ticker": ticker,
            "level": imp.get("level"),
            "sector": imp.get("sector"),
            "raw_impact": round(raw, 6),
            "applied_pct": round(pct, 6),
        })

    logger.info(
        "Event '%s' (type=%s severity=%.2f) price shocks applied to %d assets",
        event.title, event.type, event.severity, len(applied),
    )
    return applied


def init_event_engine(gen: EventGenerator, prop: EventPropagation):
    """初始化事件引擎实例"""
    global _event_generator, _event_propagation
    _event_generator = gen
    _event_propagation = prop


@router.get("", response_model=List[NewsResponse])
async def list_news(
    world_id: int = Query(1),
    limit: int = Query(50, le=200),
    importance: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """获取新闻列表（与 /news 同源：news 表，按 world 过滤）"""
    query = select(News).where(News.world_id == world_id).order_by(News.created_at.desc())

    if importance:
        query = query.where(News.importance == importance.upper())

    query = query.limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/list")
async def list_events(
    world_id: int = Query(1),
    limit: int = Query(50, le=200),
    event_type: Optional[str] = None,
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session)
):
    """获取事件列表"""
    query = (
        select(Event)
        .where(Event.world_id == world_id)
        .order_by(Event.created_at.desc())
    )
    
    if event_type:
        query = query.where(func.lower(Event.type) == event_type.lower())
    
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
            "duration_days": e.duration_days or 0,
            # 数据来源标注：事件为模拟事件引擎生成
            "data_source": DataSource.SIMULATED.value,
        }
        for e in events
    ]


@router.get("/timeline/{ticker}")
async def get_asset_timeline(
    ticker: str,
    world_id: int = Query(1),
    limit: int = Query(50, le=200),
    world: World = Depends(get_world_or_404),
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
            "created_at": e.created_at.isoformat(),
            "data_source": DataSource.SIMULATED.value,
        }
        for e in events
    ]


@router.post("/generate")
async def generate_event(
    world_id: int,
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session)
):
    """生成新事件：基于该世界真实资产生成 -> 落库 -> 施加价格冲击。

    旧实现里 `select(Event).__table__.c` 是无效死代码（AttributeError 500），
    且用 TEST0..9 假资产生成；这里改为查 assets 表取真实资产，
    返回结构与 /events/list 完全一致。
    """
    if not _event_generator:
        raise HTTPException(status_code=503, detail="Event generator not initialized")

    # 获取当前世界的真实资产
    rows = (await session.execute(
        select(Asset.ticker, Asset.sector).where(Asset.world_id == world_id)
    )).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No assets found for world {world_id}")

    assets = [{"ticker": t, "sector": s or "Unknown"} for t, s in rows]
    sectors = list({a["sector"] for a in assets})

    event = _event_generator.generate_event(assets=assets, sectors=sectors)
    await persist_event(world_id, event, session)

    # 与每日生成路径一致：把事件影响封顶(±5%)后按波动率/类型差异化传导到行情
    try:
        apply_event_price_shocks(event, assets)
    except Exception as e:
        logger.warning(f"Event propagation after generate failed: {e}")

    return {
        "id": event.id,
        "type": event.type,
        "severity": event.severity,
        "title": event.title,
        "body": event.body,
        "affected_assets": event.affected_assets,
        "affected_sectors": event.affected_sectors,
        "sentiment_effect": event.sentiment_effect,
        "created_at": event.created_at.isoformat(),
        "duration_days": event.duration_days or 0,
        "data_source": "SIMULATED",
    }


@router.get("/propagation-summary")
async def get_propagation_summary(
    limit: int = Query(20, le=100)
):
    """获取事件传播摘要"""
    if not _event_propagation:
        return []
    
    return _event_propagation.get_propagation_summary(limit)


async def persist_event(world_id: int, ev: SimEvent, session: AsyncSession) -> None:
    """把一个由 EventGenerator 产生的内存事件落库到 events 表。"""
    from app.models import Event as DBEvent
    db_event = DBEvent(
        id=ev.id,
        world_id=world_id,
        type=ev.type,
        severity=ev.severity,
        title=ev.title,
        body=ev.body,
        affected_assets=ev.affected_assets,
        affected_sectors=ev.affected_sectors,
        macro_effect=ev.macro_effect,
        sentiment_effect=ev.sentiment_effect,
        duration_days=ev.duration_days,
        created_at=ev.created_at,
    )
    session.add(db_event)
    await session.commit()
