"""
FinanceSim Simulation Router
模拟控制 API
"""
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import World
from app.engines.simulation_engine import SimulationClock, SimulationSpeed

router = APIRouter(prefix="/simulation", tags=["simulation"])

# 全局模拟时钟（按 world_id 管理）
sim_clocks = {}


def get_sim_clock(world_id: int) -> SimulationClock:
    if world_id not in sim_clocks:
        sim_clocks[world_id] = SimulationClock()
    return sim_clocks[world_id]


@router.get("/{world_id}/status", response_model=Dict)
async def get_status(world_id: int):
    """获取模拟状态"""
    clock = get_sim_clock(world_id)
    return clock.get_status()


@router.post("/{world_id}/start")
async def start_simulation(world_id: int):
    """开始模拟"""
    clock = get_sim_clock(world_id)
    clock.start()
    return {"status": "started"}


@router.post("/{world_id}/pause")
async def pause_simulation(world_id: int):
    """暂停模拟"""
    clock = get_sim_clock(world_id)
    clock.pause()
    return {"status": "paused"}


@router.post("/{world_id}/speed")
async def set_speed(world_id: int, speed: str):
    """设置速度"""
    try:
        sim_speed = SimulationSpeed[speed.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid speed: {speed}")
    
    clock = get_sim_clock(world_id)
    clock.set_speed(sim_speed)
    return {"speed": speed}


@router.post("/{world_id}/tick")
async def tick(world_id: int):
    """执行一个 tick"""
    clock = get_sim_clock(world_id)
    new_day = clock.tick()
    return {
        "current_day": clock.current_day,
        "new_day": new_day
    }


@router.post("/{world_id}/step")
async def step(world_id: int, days: int = 1):
    """步进指定天数"""
    clock = get_sim_clock(world_id)
    new_day = clock.step(days)
    return {"current_day": new_day}
