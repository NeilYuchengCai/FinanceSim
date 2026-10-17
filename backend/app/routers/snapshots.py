"""
FinanceSim Snapshot Router
快照 API：创建、列出、恢复、分支
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_world_or_404
from app.models import World
from app.services.snapshot_service import SnapshotService

router = APIRouter(prefix="/worlds/{world_id}/snapshots", tags=["snapshots"])


@router.post("")
async def create_snapshot(
    world_id: int,
    name: str = Query(..., description="快照名称"),
    description: Optional[str] = Query(None, description="快照描述"),
    session: AsyncSession = Depends(get_session),
    world: World = Depends(get_world_or_404),
):
    """创建世界快照"""
    try:
        result = await SnapshotService.create_snapshot(session, world_id, name, description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_snapshots(
    world_id: int,
    session: AsyncSession = Depends(get_session),
    world: World = Depends(get_world_or_404),
):
    """列出世界的所有快照"""
    return await SnapshotService.list_snapshots(session, world_id)


@router.post("/{snapshot_id}/restore")
async def restore_snapshot(
    world_id: int,
    snapshot_id: int,
    session: AsyncSession = Depends(get_session),
    world: World = Depends(get_world_or_404),
):
    """恢复到指定快照"""
    try:
        result = await SnapshotService.restore_snapshot(session, world_id, snapshot_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{snapshot_id}/branch")
async def branch_world(
    world_id: int,
    snapshot_id: int,
    new_world_name: str = Query(..., description="新世界名称"),
    session: AsyncSession = Depends(get_session),
    world: World = Depends(get_world_or_404),
):
    """从快照分支创建新世界"""
    try:
        result = await SnapshotService.branch_world(session, world_id, snapshot_id, new_world_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{snapshot_id}")
async def delete_snapshot(
    world_id: int,
    snapshot_id: int,
    session: AsyncSession = Depends(get_session),
    world: World = Depends(get_world_or_404),
):
    """删除快照"""
    from app.models import WorldSnapshot
    snapshot = await session.get(WorldSnapshot, snapshot_id)
    if not snapshot or snapshot.world_id != world_id:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    await session.delete(snapshot)
    await session.commit()
    return {"message": "Snapshot deleted"}
