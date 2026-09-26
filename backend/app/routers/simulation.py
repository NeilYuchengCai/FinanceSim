"""
FinanceSim Simulation Router
模拟控制 API
"""
import logging
from datetime import datetime, timedelta
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import World
from app.engines.simulation_engine import SimulationClock, SimulationSpeed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])

# 全局模拟时钟（按 world_id 管理）
sim_clocks = {}


async def get_sim_clock(world_id: int, session: AsyncSession) -> SimulationClock:
    """获取（或按需从 worlds 表恢复）模拟时钟"""
    if world_id not in sim_clocks:
        restored_day = 0
        try:
            world = await session.get(World, world_id)
            if world is not None and world.current_day is not None:
                restored_day = int(world.current_day)
        except Exception as e:
            logger.warning(f"Failed to restore current_day for world {world_id}: {e}")
        # 模拟起点对齐到种子行情的最后一天，使新生成的日K严格排在种子数据之后，
        # Analytics 等依赖 price_history 的页面才能跟随模拟时间延伸到"当天"。
        start_time = await _seed_last_date(session) or datetime.now()
        sim_clocks[world_id] = SimulationClock(current_day=restored_day, start_time=start_time)
    return sim_clocks[world_id]


async def _seed_last_date(session: AsyncSession):
    """返回 price_history 中最大时间戳（若存在），否则 None。"""
    try:
        from sqlalchemy import text as _text
        row = (await session.execute(_text("SELECT MAX(timestamp) FROM price_history"))).scalar()
        if row is None:
            return None
        if isinstance(row, datetime):
            return row
        return datetime.fromisoformat(str(row))
    except Exception as e:
        logger.warning(f"Failed to read seed last date: {e}")
        return None


async def persist_day(world_id: int, day: int, session: AsyncSession) -> None:
    """把当前模拟天数写回 worlds 表，使天数跨进程重启保持"""
    try:
        world = await session.get(World, world_id)
        if world is None:
            return
        world.current_day = day
        await session.commit()
    except Exception as e:
        logger.warning(f"Failed to persist current_day={day} for world {world_id}: {e}")


@router.get("/{world_id}/status", response_model=Dict)
async def get_status(world_id: int, session: AsyncSession = Depends(get_session)):
    """获取模拟状态"""
    clock = await get_sim_clock(world_id, session)
    return clock.get_status()


@router.post("/{world_id}/start")
async def start_simulation(world_id: int, session: AsyncSession = Depends(get_session)):
    """开始模拟"""
    clock = await get_sim_clock(world_id, session)
    clock.start()
    return {"status": "started"}


@router.post("/{world_id}/pause")
async def pause_simulation(world_id: int, session: AsyncSession = Depends(get_session)):
    """暂停模拟"""
    clock = await get_sim_clock(world_id, session)
    clock.pause()
    return {"status": "paused"}


@router.post("/{world_id}/speed")
async def set_speed(world_id: int, speed: str, session: AsyncSession = Depends(get_session)):
    """设置速度"""
    try:
        sim_speed = SimulationSpeed[speed.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid speed: {speed}")

    clock = await get_sim_clock(world_id, session)
    clock.set_speed(sim_speed)
    return {"speed": speed}


@router.post("/{world_id}/tick")
async def tick(world_id: int, session: AsyncSession = Depends(get_session)):
    """执行一个 tick"""
    clock = await get_sim_clock(world_id, session)
    new_day = clock.tick()
    await persist_day(world_id, clock.current_day, session)

    # 进入新的一天时：推进宏观 -> 生成与市场挂钩的新闻 -> 固化日K
    if new_day:
        # 1) 推进宏观经济 1 天，使新闻叙事与真实宏观状态挂钩
        try:
            from app.routers.economy import _economic_engine
            if _economic_engine is not None:
                _economic_engine.step(1)
        except Exception as e:
            logger.error(f"macro step failed: {e}")

        # 2) 基于真实行情快照 + 宏观状态生成"与市场挂钩"的新闻
        from app.routers.news import _news_engine
        if _news_engine is not None:
            try:
                target_date = clock.current_time
                snapshot = []
                macro_state = None
                try:
                    from app.services.market_stream import get_market_stream
                    stream = get_market_stream()
                    if stream is not None:
                        snapshot = stream.snapshot_full()
                except Exception:
                    pass
                try:
                    from app.routers.economy import _economic_engine
                    if _economic_engine is not None:
                        macro_state = _economic_engine.get_macro_data()
                except Exception:
                    pass
                _news_engine.generate_for_date(target_date, snapshot, macro_state)
            except Exception as e:
                logger.error(f"Daily news generation failed: {e}")

        # 3) 把当前内存价格固化为日K，使 Analytics 跟随模拟时间延伸
        try:
            from app.services.market_stream import get_market_stream
            stream = get_market_stream()
            if stream is not None:
                await stream.record_daily_bar(clock.current_day, clock.current_time)
        except Exception as e:
            logger.error(f"record_daily_bar failed: {e}")

    return {
        "current_day": clock.current_day,
        "new_day": new_day
    }


@router.post("/{world_id}/step")
async def step(world_id: int, days: int = 1, session: AsyncSession = Depends(get_session)):
    """步进指定天数"""
    clock = await get_sim_clock(world_id, session)
    old_day = clock.current_day
    new_day = clock.step(days)
    await persist_day(world_id, new_day, session)

    # 步进期间跨越的每一天都补：推进宏观 -> 生成与市场挂钩的新闻 -> 固化日K
    from app.routers.news import _news_engine
    if _news_engine is not None:
        from app.services.market_stream import get_market_stream
        stream = get_market_stream()
        for d in range(old_day + 1, new_day + 1):
            try:
                day_date = (clock.start_time + timedelta(days=d)).date()
                day_dt = datetime.combine(day_date, datetime.min.time())

                # 推进宏观 1 天
                try:
                    from app.routers.economy import _economic_engine
                    if _economic_engine is not None:
                        _economic_engine.step(1)
                except Exception as e:
                    logger.error(f"macro step failed on day {d}: {e}")

                # 推进真实行情：快进不经过实时 tick 循环，这里手动推进若干 tick 让价格真实演化，
                # 使当日新闻有真实涨跌幅、Analytics 蜡烛有实体（而非停留在 Flat 的水平线）
                if stream is not None:
                    for _ in range(500):
                        try:
                            stream.advance()
                        except Exception:
                            break

                # 基于真实行情 + 宏观生成当日新闻
                snapshot = stream.snapshot_full() if stream else []
                macro_state = None
                try:
                    from app.routers.economy import _economic_engine
                    if _economic_engine is not None:
                        macro_state = _economic_engine.get_macro_data()
                except Exception:
                    pass
                _news_engine.generate_for_date(day_dt, snapshot, macro_state)

                # 固化日K，使 Analytics 延伸到当日
                if stream is not None:
                    try:
                        await stream.record_daily_bar(d, day_dt)
                    except Exception as e:
                        logger.error(f"record_daily_bar failed on day {d}: {e}")
            except Exception as e:
                logger.error(f"News generation for step day {d} failed: {e}")

    return {"current_day": new_day}


@router.post("/{world_id}/reset")
async def reset_simulation(world_id: int, session: AsyncSession = Depends(get_session)):
    """重置模拟，从零开始"""
    clock = await get_sim_clock(world_id, session)
    clock.reset()
    await persist_day(world_id, 0, session)
    return {"status": "reset", "current_day": 0}


@router.post("/{world_id}/restore")
async def restore_simulation(world_id: int, day: int = Query(0, ge=0), session: AsyncSession = Depends(get_session)):
    """从指定天数恢复模拟状态"""
    clock = await get_sim_clock(world_id, session)
    clock.reset()
    if day > 0:
        clock.step(day)
    await persist_day(world_id, clock.current_day, session)
    return {"status": "restored", "current_day": clock.current_day}
