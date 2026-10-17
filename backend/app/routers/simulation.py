"""
FinanceSim Simulation Router
模拟控制 API
"""
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_world_or_404
from app.models import World
from app.engines.simulation_engine import SimulationClock, SimulationSpeed
from app.services.market_stream import get_market_stream

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
        start_time = await _seed_last_date(session, world_id) or datetime.now()
        sim_clocks[world_id] = SimulationClock(current_day=restored_day, start_time=start_time)
    return sim_clocks[world_id]


async def _seed_last_date(session: AsyncSession, world_id: int):
    """返回指定世界 price_history 中的最大时间戳（若存在），否则 None。

    必须按 world 过滤（price_history 经 assets.world_id 关联），否则多世界并存时
    会用别处的种子日期作为本世界的模拟起点，造成日K 日期串味。
    """
    try:
        from sqlalchemy import text as _text
        row = (await session.execute(_text(
            "SELECT MAX(ph.timestamp) FROM price_history ph "
            "JOIN assets a ON a.id = ph.asset_id WHERE a.world_id = :wid"
        ), {"wid": world_id})).scalar()
        if row is None:
            return None
        if isinstance(row, datetime):
            return row
        return datetime.fromisoformat(str(row))
    except Exception as e:
        logger.warning(f"Failed to read seed last date for world {world_id}: {e}")
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
async def get_status(world_id: int, session: AsyncSession = Depends(get_session),
                   world: World = Depends(get_world_or_404)):
    """获取模拟状态"""
    clock = await get_sim_clock(world_id, session)
    return clock.get_status()


@router.post("/{world_id}/start")
async def start_simulation(world_id: int, session: AsyncSession = Depends(get_session),
                          world: World = Depends(get_world_or_404)):
    """开始模拟"""
    clock = await get_sim_clock(world_id, session)
    clock.start()
    return {"status": "started"}


@router.post("/{world_id}/pause")
async def pause_simulation(world_id: int, session: AsyncSession = Depends(get_session),
                           world: World = Depends(get_world_or_404)):
    """暂停模拟"""
    clock = await get_sim_clock(world_id, session)
    clock.pause()
    return {"status": "paused"}


@router.post("/{world_id}/speed")
async def set_speed(world_id: int, speed: str, session: AsyncSession = Depends(get_session),
                    world: World = Depends(get_world_or_404)):
    """设置速度"""
    try:
        sim_speed = SimulationSpeed[speed.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid speed: {speed}")

    clock = await get_sim_clock(world_id, session)
    clock.set_speed(sim_speed)
    return {"speed": speed}


@router.post("/{world_id}/tick")
async def tick(world_id: int, session: AsyncSession = Depends(get_session),
             world: World = Depends(get_world_or_404)):
    """执行一个 tick"""
    clock = await get_sim_clock(world_id, session)
    new_day = clock.tick()
    await persist_day(world_id, clock.current_day, session)

    if clock.is_paused:
        return {
            "current_day": clock.current_day,
            "new_day": False,
            "paused": True
        }

    # 进入新的一天时：推进宏观 -> AI 交易 -> 生成事件(落库+冲击) -> 新闻 -> 固化日K
    if new_day:
        day_dt = clock.start_time + timedelta(days=clock.current_day)
        await _run_daily_generators(world_id, session, clock.current_day, day_dt)

    return {
        "current_day": clock.current_day,
        "new_day": new_day
    }


@router.post("/{world_id}/step")
async def step(world_id: int, days: int = 1, session: AsyncSession = Depends(get_session),
             world: World = Depends(get_world_or_404)):
    """步进指定天数"""
    clock = await get_sim_clock(world_id, session)
    old_day = clock.current_day
    new_day = clock.step(days)
    await persist_day(world_id, new_day, session)

    stream = get_market_stream()
    for d in range(old_day + 1, new_day + 1):
        try:
            day_date = (clock.start_time + timedelta(days=d)).date()
            day_dt = datetime.combine(day_date, datetime.min.time())
            # 快进不经过实时 tick 循环，这里手动推进若干 tick 让价格真实演化
            if stream is not None:
                for _ in range(500):
                    try:
                        stream.advance()
                    except Exception:
                        break
            await _run_daily_generators(world_id, session, d, day_dt)
        except Exception as e:
            logger.error(f"Daily updates for step day {d} failed: {e}")

    return {"current_day": new_day}


async def _persist_macro_snapshot(world_id: int, day: int, session: AsyncSession) -> None:
    """把当前宏观状态固化一行 MacroSnapshot（此前该表无任何写入方）。"""
    from app.models import MacroSnapshot
    from app.routers.economy import _economic_engine

    if _economic_engine is None:
        return
    state = _economic_engine.state
    snapshot = MacroSnapshot(
        world_id=world_id,
        day=day,
        gdp_growth=state.gdp_growth,
        inflation=state.inflation,
        unemployment=state.unemployment,
        interest_rate=state.interest_rate,
        money_supply=state.money_supply,
        consumer_confidence=state.consumer_confidence,
        industrial_production=state.industrial_production,
        cycle_phase=state.cycle_phase,
        cycle_position=state.cycle_position,
    )
    session.add(snapshot)
    await session.commit()


async def _persist_news(world_id: int, news_items: list, session: AsyncSession) -> None:
    """把当日生成的新闻批量写入 news 表（此前只停留在引擎内存）。"""
    from app.models import News

    rows = []
    for n in news_items:
        created_at = n.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = None
        rows.append(News(
            id=n.get("id") or str(uuid.uuid4()),
            world_id=world_id,
            headline=n.get("headline") or "",
            body=n.get("body") or "",
            importance=n.get("importance") or "MARKET",
            sentiment=n.get("sentiment"),
            affected_assets=n.get("affected_assets") or [],
            created_at=created_at,
        ))
    if not rows:
        return
    session.add_all(rows)
    await session.commit()


async def _run_daily_generators(world_id: int, session: AsyncSession, day: int, day_dt: datetime) -> None:
    """推进一天的世界演化：宏观 -> AI 交易 -> 事件(落库+价格冲击) -> 新闻 -> 固化日K。"""
    # 1) 推进宏观经济 1 天
    try:
        from app.routers.economy import _economic_engine
        if _economic_engine is not None:
            _economic_engine.step(1)
    except Exception as e:
        logger.error(f"macro step failed: {e}")

    # 1b) 宏观日快照落库，使 /economy/history 有真实历史可查
    try:
        await _persist_macro_snapshot(world_id, day, session)
    except Exception as e:
        logger.error(f"macro snapshot persist failed: {e}")

    # 2) AI 交易员自动交易（真实引擎 + 实时行情），制造市场活动
    try:
        from app.routers.bot import run_bots_for_world
        run_bots_for_world(world_id)
    except Exception as e:
        logger.error(f"bot step failed: {e}")

    # 3) 生成与市场挂钩的事件，持久化并施加价格冲击
    try:
        from app.routers.events import _event_generator, _event_propagation, persist_event
        stream = get_market_stream()
        assets = []
        if stream is not None:
            assets = [{"ticker": s["t"], "sector": s.get("s") or "Unknown"} for s in stream.snapshot_full()]
        if _event_generator is not None and assets and random.random() < 0.7:
            ev = _event_generator.generate_event(assets, list({a["sector"] for a in assets}))
            await persist_event(world_id, ev, session)
            if _event_propagation is not None and stream is not None:
                for imp in _event_propagation.propagate(ev, assets):
                    tk = imp.get("ticker")
                    if tk and tk != "MACRO":
                        stream.apply_shock(tk, float(imp.get("impact", 0.0)) * 0.12)
    except Exception as e:
        logger.error(f"event generation failed: {e}")

    # 4) 基于真实行情 + 宏观生成当日新闻，并落库到 news 表
    try:
        from app.routers.news import _news_engine
        if _news_engine is not None:
            snapshot = []
            macro_state = None
            try:
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
            generated = _news_engine.generate_for_date(day_dt, snapshot, macro_state)
            await _persist_news(world_id, generated, session)
    except Exception as e:
        logger.error(f"Daily news generation failed: {e}")

    # 5) 固化日K，使 Analytics 跟随模拟时间延伸
    try:
        stream = get_market_stream()
        if stream is not None:
            await stream.record_daily_bar(day, day_dt)
    except Exception as e:
        logger.error(f"record_daily_bar failed: {e}")


@router.post("/{world_id}/reset")
async def reset_simulation(world_id: int, session: AsyncSession = Depends(get_session),
                           world: World = Depends(get_world_or_404)):
    """重置模拟，从零开始"""
    clock = await get_sim_clock(world_id, session)
    clock.reset(day=0)
    await persist_day(world_id, 0, session)
    return {"status": "reset", "current_day": 0}


@router.post("/{world_id}/restore")
async def restore_simulation(world_id: int, day: int = Query(0, ge=0),
                             session: AsyncSession = Depends(get_session),
                             world: World = Depends(get_world_or_404)):
    """从指定天数恢复模拟状态。

    与 step 同路径：重置时钟到目标天数（保留种子起点日期，不用今天），
    再逐天重放日级生成器（宏观/交易/事件/新闻/日K），使 events、news、
    price_history 与 clock 三者自洽——而不是只改一个天数数字。
    """
    clock = await get_sim_clock(world_id, session)
    clock.reset(day=day)
    await persist_day(world_id, clock.current_day, session)

    # 幂等：清掉目标天数以内的宏观快照，避免重复 restore 时 /economy/history
    # 出现同日期的重复点（price_history 的日K 本身按 world_day 幂等）。
    try:
        from sqlalchemy import delete
        from app.models import MacroSnapshot
        await session.execute(
            delete(MacroSnapshot).where(
                MacroSnapshot.world_id == world_id,
                MacroSnapshot.day <= day,
            )
        )
        await session.commit()
    except Exception as e:
        logger.warning(f"Failed to clear macro snapshots before restore: {e}")

    for d in range(1, day + 1):
        day_dt = clock.start_time + timedelta(days=d)
        try:
            await _run_daily_generators(world_id, session, d, day_dt)
        except Exception as e:
            logger.error(f"restore day {d} failed: {e}")
    return {"status": "restored", "current_day": clock.current_day}
