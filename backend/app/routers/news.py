"""
FinanceSim News Router
新闻 API

铁律①/④ 治理后的统一实现：
- 新闻是"模拟（SIMULATED）"类别，所有新闻生成都基于世界真实资产（Asset 表）+
  真实行情快照 + 真实宏观状态，杜绝硬编码美股/宏观冒充真实（F-1-1/F-1-2）。
- 新闻生成/演化统一落 News 表（单一真相源）；GET /news、/headlines、/briefing、
  /impact-summary、/daily-summary 全部从 News 表按 world_id 读取，消除内存引擎与
  DB 双源矛盾（F-1-2）。
- 数据来源标注统一用 DataSource 枚举常量（铁律④）。
"""
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_session
from app.models import News, Asset
from app.engines import NewsEngine
from app.core.datasource import DataSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news"])

_news_engine: Optional[NewsEngine] = None


def init_news_engine(engine: NewsEngine):
    """初始化新闻引擎实例"""
    global _news_engine
    _news_engine = engine


# 重要性排序（与新闻引擎 NewsImportance 枚举顺序一致），用于简报排序
_IMP_ORDER = {"BREAKING": 0, "MAJOR": 1, "MARKET": 2, "COMPANY": 3, "MACRO": 4, "MINOR": 5}


def _imp_rank(n: News) -> int:
    return _IMP_ORDER.get((n.importance or "MARKET"), 2)


def _row_to_dict(n: News) -> dict:
    """把 News ORM 行序列化为前端契约（与历史 /news 口径一致）。

    新闻属 SIMULATED 类别，data_source 在序列化层标注清楚（铁律④）。
    """
    return {
        "id": n.id,
        "headline": n.headline,
        "body": n.body,
        "importance": n.importance,
        "sentiment": n.sentiment,
        # 前端历史上传的是 category 参数，取值与重要度一致，这里用 importance 充当
        "category": n.importance,
        "affected_assets": n.affected_assets or [],
        "source": "FINANCESIM",
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "is_read": False,
        "data_source": DataSource.SIMULATED.value,
    }


async def _recent_news(session: AsyncSession, world_id: int, limit: int) -> List[News]:
    """按 world_id 取最近 limit 条新闻（created_at 倒序）。"""
    result = await session.execute(
        select(News)
        .where(News.world_id == world_id)
        .order_by(News.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def _ensure_db_news(session: AsyncSession, world_id: int) -> None:
    """用世界真实资产 + 真实行情快照 + 真实宏观生成当日新闻并落库。

    仅在 DB 中该世界尚无新闻时调用，避免重复生成。删除旧版硬编码美股/宏观，
    全部来自世界真实数据（F-1-1/F-1-2）。
    """
    rows = (
        await session.execute(
            select(Asset.ticker, Asset.sector).where(Asset.world_id == world_id)
        )
    ).all()
    if not rows:
        logger.warning("No assets for world %s, skip news generation", world_id)
        return

    asset_list = [{"ticker": t, "sector": s or "Unknown"} for t, s in rows]
    snapshot: List[dict] = []
    macro = None
    try:
        from app.services.market_stream import get_market_stream
        stream = get_market_stream()
        if stream is not None:
            snapshot = stream.snapshot_full()
    except Exception as exc:  # 行情流未就绪时退化为纯资产维度
        logger.warning("market_stream unavailable for news gen: %s", exc)
        snapshot = []
    try:
        from app.routers.economy import _economic_engine
        if _economic_engine is not None:
            macro = _economic_engine.get_macro_data()
    except Exception as exc:
        logger.warning("economic engine unavailable for news gen: %s", exc)
        macro = None

    day_dt = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
    if _news_engine is None:
        return
    generated = _news_engine.generate_for_date(day_dt, snapshot, macro)
    if not generated:
        return
    # 统一落库路径（单一真相源）
    from app.routers.simulation import _persist_news
    await _persist_news(world_id, generated, session)
    logger.info("Ensured %d news persisted for world %s", len(generated), world_id)


def _build_briefing(rows: List[News], hours: int) -> dict:
    """从 News 行计算每日简报（与新闻引擎 get_briefing 口径一致）。"""
    if not rows:
        return {
            "period": f"Last {hours} hours",
            "total_items": 0,
            "breaking_count": 0,
            "major_count": 0,
            "sentiment_index": 0.0,
            "sentiment_label": "Neutral",
            "by_category": {},
            "top_stories": [],
            "market_impact_summary": "No recent news affecting markets.",
        }
    sentiments = [n.sentiment for n in rows if n.sentiment is not None]
    avg = sum(sentiments) / len(sentiments) if sentiments else 0.0
    breaking = [n for n in rows if n.importance == "BREAKING"]
    major = [n for n in rows if n.importance == "MAJOR"]
    by_category: dict = {}
    for n in rows:
        cat = n.importance or "MARKET"
        by_category.setdefault(cat, []).append(n)
    top_stories = sorted(rows, key=_imp_rank)[:5]
    if breaking:
        summary = f"⚠️ BREAKING: {breaking[0].headline}"
    elif major:
        summary = f"📰 Major developments: {major[0].headline}"
    elif avg > 0.3:
        summary = "📈 Positive sentiment driving market optimism"
    elif avg < -0.3:
        summary = "📉 Negative sentiment weighing on markets"
    else:
        summary = "⚖️ Mixed signals across market news"
    return {
        "period": f"Last {hours} hours",
        "total_items": len(rows),
        "breaking_count": len(breaking),
        "major_count": len(major),
        "sentiment_index": round(avg, 3),
        "sentiment_label": "Bullish" if avg > 0.2 else ("Bearish" if avg < -0.2 else "Neutral"),
        "by_category": {
            cat: {
                "count": len(items),
                "avg_sentiment": round(
                    sum(x.sentiment for x in items if x.sentiment is not None)
                    / max(1, len([x for x in items if x.sentiment is not None])),
                    3,
                ),
                "top_story": _row_to_dict(items[0]),
            }
            for cat, items in by_category.items()
        },
        "top_stories": [_row_to_dict(s) for s in top_stories],
        "market_impact_summary": summary,
    }


def _build_daily_summary(rows: List[News], target_date: date) -> dict:
    """从 News 行计算指定日期的摘要（与新闻引擎 get_daily_summary 口径一致）。"""
    if not rows:
        return {
            "date": target_date.isoformat(),
            "total_news": 0,
            "summary": "No news recorded for this day",
            "highlight": None,
            "market_sentiment": "Neutral",
        }
    sentiments = [n.sentiment for n in rows if n.sentiment is not None]
    avg = sum(sentiments) / len(sentiments) if sentiments else 0.0
    breaking = [n for n in rows if n.importance == "BREAKING"]
    major = [n for n in rows if n.importance == "MAJOR"]
    most = max(rows, key=lambda x: abs(x.sentiment or 0.0))
    parts = []
    if avg > 0.3:
        parts.append("Markets closed on a strongly positive note.")
    elif avg > 0.1:
        parts.append("Markets showed moderate optimism.")
    elif avg < -0.3:
        parts.append("Markets faced significant headwinds.")
    elif avg < -0.1:
        parts.append("Markets experienced some weakness.")
    else:
        parts.append("Markets traded in a mixed fashion.")
    if breaking:
        parts.append(f"Breaking: {breaking[0].headline}")
    if major:
        parts.append(f"Key development: {major[0].headline}")
    return {
        "date": target_date.isoformat(),
        "total_news": len(rows),
        "breaking_count": len(breaking),
        "major_count": len(major),
        "summary": " ".join(parts),
        "highlight": _row_to_dict(most),
        "market_sentiment": "Bullish" if avg > 0.2 else ("Bearish" if avg < -0.2 else "Neutral"),
        "sentiment_score": round(avg, 3),
        "news_items": [_row_to_dict(n) for n in sorted(rows, key=_imp_rank)[:10]],
    }


@router.get("")
async def list_news(
    world_id: int = Query(1),
    limit: int = Query(50, le=200),
    category: Optional[str] = None,
    importance: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """获取新闻列表（DB 单一真相源，按 world 过滤）。

    前端历史上传的是 category 参数，取值（BREAKING/MAJOR/MARKET/COMPANY/MACRO）
    与新闻重要度一致，这里作为 importance 的别名兼容处理。
    """
    query = select(News).where(News.world_id == world_id).order_by(News.created_at.desc())

    level = (importance or category or "").upper() or None
    if level:
        query = query.where(News.importance == level)

    query = query.limit(max(1, min(limit, 200)))
    result = await session.execute(query)
    news_rows = result.scalars().all()

    return [_row_to_dict(n) for n in news_rows]


@router.get("/briefing")
async def get_briefing(
    hours: int = Query(24, ge=1, le=168),
    world_id: int = Query(1),
    session: AsyncSession = Depends(get_session),
):
    """获取新闻简报（从 News 表按 world_id 读取，单一真相源）。"""
    rows = await _recent_news(session, world_id, limit=200)
    if not rows:
        await _ensure_db_news(session, world_id)
        rows = await _recent_news(session, world_id, limit=200)
    return _build_briefing(rows, hours)


@router.get("/headlines")
async def get_headlines(
    limit: int = Query(10, le=50),
    world_id: int = Query(1),
    session: AsyncSession = Depends(get_session),
):
    """获取头条新闻（从 News 表按 world_id 读取，单一真相源）。"""
    rows = await _recent_news(session, world_id, limit=limit)
    if not rows:
        await _ensure_db_news(session, world_id)
        rows = await _recent_news(session, world_id, limit=limit)
    return [_row_to_dict(n) for n in rows]


@router.get("/daily-summary/{day_offset}")
async def get_daily_summary(
    day_offset: int = Path(..., ge=-30, le=0),
    world_id: int = Query(1),
    session: AsyncSession = Depends(get_session),
):
    """获取指定日期的新闻摘要（从 News 表按 world_id + 日期读取）。"""
    target_date = date.today() - timedelta(days=day_offset)
    result = await session.execute(
        select(News)
        .where(News.world_id == world_id, func.date(News.created_at) == target_date.isoformat())
        .order_by(News.created_at.desc())
    )
    rows = list(result.scalars().all())
    return _build_daily_summary(rows, target_date)


@router.get("/impact-summary")
async def get_impact_summary(
    world_id: int = Query(1),
    session: AsyncSession = Depends(get_session),
):
    """获取最新市场影响摘要（从 News 表按 world_id 读取）。"""
    rows = await _recent_news(session, world_id, limit=200)
    if not rows:
        await _ensure_db_news(session, world_id)
        rows = await _recent_news(session, world_id, limit=200)
    briefing = _build_briefing(rows, 24)
    return {
        "impact_summary": briefing.get("market_impact_summary", "No recent impact"),
        "sentiment_index": briefing.get("sentiment_index", 0),
        "sentiment_label": briefing.get("sentiment_label", "Neutral"),
        "breaking_count": briefing.get("breaking_count", 0),
        "total_items": briefing.get("total_items", 0),
    }


@router.post("/generate")
async def generate_news(
    force: bool = Query(False),
    days: int = Query(1, ge=1, le=30),
    world_id: int = Query(1),
    session: AsyncSession = Depends(get_session),
):
    """生成新闻并落库（基于世界真实资产 + 真实行情 + 真实宏观，杜绝硬编码）。

    删除旧版硬编码美股 AAPL/MSFT/GOOGL/JPM/JNJ 与硬编码 macro_state，改为从
    Asset 表按 world_id 取真实资产与板块、配合行情快照与宏观引擎生成；生成的新闻
    统一写入 News 表（带 world_id、data_source=SIMULATED 标注），保证模拟运行中
    新闻自动生成且 GET /news 能读到。
    """
    if not _news_engine:
        raise HTTPException(status_code=503, detail="News engine not initialized")

    # 从 Asset 表取世界真实资产与板块（F-1-1/F-1-2：删除硬编码美股/宏观）
    rows = (
        await session.execute(
            select(Asset.ticker, Asset.sector).where(Asset.world_id == world_id)
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No assets found for world {world_id}")

    asset_list = [{"ticker": t, "sector": s or "Unknown"} for t, s in rows]

    snapshot: List[dict] = []
    macro = None
    try:
        from app.services.market_stream import get_market_stream
        stream = get_market_stream()
        if stream is not None:
            snapshot = stream.snapshot_full()
    except Exception as exc:
        logger.warning("market_stream unavailable for news gen: %s", exc)
        snapshot = []
    try:
        from app.routers.economy import _economic_engine
        if _economic_engine is not None:
            macro = _economic_engine.get_macro_data()
    except Exception as exc:
        logger.warning("economic engine unavailable for news gen: %s", exc)
        macro = None

    # 每个模拟日用不同日期派生可复现随机源（避免重复生成同一批新闻）
    base_dt = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
    news_list: List[dict] = []
    for i in range(days):
        day_dt = base_dt - timedelta(days=i)
        batch = _news_engine.generate_for_date(day_dt, snapshot, macro)
        news_list.extend(batch)

    # 统一落库路径（单一真相源）
    from app.routers.simulation import _persist_news
    await _persist_news(world_id, news_list, session)

    return {
        "generated": len(news_list),
        "news": news_list[:20],  # 返回最近20条
    }
