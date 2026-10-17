"""
FinanceSim World Router
世界管理 API
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models import World
from app.schemas import WorldCreate, WorldResponse

router = APIRouter(prefix="/worlds", tags=["worlds"])


@router.post("", response_model=WorldResponse)
async def create_world(world_data: WorldCreate, session: AsyncSession = Depends(get_session)):
    """创建新世界"""
    world = World(
        name=world_data.name,
        mode=world_data.mode,
        seed=world_data.seed or str(uuid.uuid4())[:8],
        # 此前 starting_capital / simulation_speed / difficulty 被创建接口丢弃，
        # 世界行里永远只有默认值；这里按请求写入，交易与模拟才能真正按参数运行。
        starting_capital=world_data.starting_capital,
        simulation_speed=world_data.simulation_speed,
        difficulty=world_data.difficulty,
    )
    session.add(world)
    await session.commit()
    await session.refresh(world)
    return world


@router.get("", response_model=List[WorldResponse])
async def list_worlds(session: AsyncSession = Depends(get_session)):
    """获取世界列表"""
    result = await session.execute(select(World).order_by(World.created_at.desc()))
    worlds = result.scalars().all()
    return worlds


@router.get("/{world_id}", response_model=WorldResponse)
async def get_world(world_id: int, session: AsyncSession = Depends(get_session)):
    """获取单个世界"""
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    return world


@router.delete("/{world_id}")
async def delete_world(world_id: int, session: AsyncSession = Depends(get_session)):
    """删除世界"""
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    
    await session.delete(world)
    await session.commit()
    return {"message": "World deleted"}
