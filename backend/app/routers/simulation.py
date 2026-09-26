"""
FinanceSim Simulation Router
模拟控制 API
"""
import logging
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
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
        sim_clocks[world_id] = SimulationClock(current_day=restored_day)
    return sim_clocks[world_id]


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
    return {
        "current_day": clock.current_day,
        "new_day": new_day
    }


@router.post("/{world_id}/step")
async def step(world_id: int, days: int = 1, session: AsyncSession = Depends(get_session)):
    """步进指定天数"""
    clock = await get_sim_clock(world_id, session)
    new_day = clock.step(days)
    await persist_day(world_id, new_day, session)
    return {"current_day": new_day}
