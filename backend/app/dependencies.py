"""
FinanceSim 共享依赖

放置跨路由复用的 FastAPI 依赖，避免每个路由各写一遍世界校验。
"""
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import World


async def get_world_or_404(
    world_id: int,
    session: AsyncSession = Depends(get_session),
) -> World:
    """世界级端点的统一校验：world 不存在时返回 404，而不是返回假数据。

    依赖声明为返回 World 对象，路由函数可直接用 `world: World = Depends(get_world_or_404)`
    拿到已校验的世界行；仅需校验时可忽略返回值。
    """
    world = await session.get(World, world_id)
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return world
