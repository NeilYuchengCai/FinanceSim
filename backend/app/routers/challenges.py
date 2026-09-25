"""
FinanceSim Challenge Router
挑战模式 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.database import get_session
from app.models import World, Challenge, ChallengeProgress

router = APIRouter(prefix="/challenges", tags=["challenges"])


@router.post("")
async def create_challenge(
    world_id: int,
    challenge_type: str = Query(...),
    name: str = Query(...),
    description: Optional[str] = Query(None),
    target_days: int = Query(...),
    constraints: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """创建挑战"""
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    try:
        constraints_data = json.loads(constraints) if constraints else {}
    except json.JSONDecodeError:
        constraints_data = {}

    challenge = Challenge(
        world_id=world_id,
        challenge_type=challenge_type,
        name=name,
        description=description,
        target_days=target_days,
        constraints=constraints_data,
        status="active",
    )
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)
    return {
        "id": challenge.id,
        "world_id": challenge.world_id,
        "type": challenge.challenge_type,
        "name": challenge.name,
        "description": challenge.description,
        "target_days": challenge.target_days,
        "constraints": challenge.constraints,
        "status": challenge.status,
    }


@router.get("/world/{world_id}")
async def list_world_challenges(
    world_id: int,
    session: AsyncSession = Depends(get_session),
):
    """列出世界的挑战"""
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    result = await session.execute(
        select(Challenge).where(Challenge.world_id == world_id).order_by(Challenge.created_at.desc())
    )
    challenges = result.scalars().all()
    return [
        {
            "id": c.id,
            "type": c.challenge_type,
            "name": c.name,
            "description": c.description,
            "target_days": c.target_days,
            "constraints": c.constraints,
            "status": c.status,
            "created_at": c.created_at.isoformat(),
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        }
        for c in challenges
    ]


@router.get("/{challenge_id}/progress")
async def get_challenge_progress(
    challenge_id: int,
    session: AsyncSession = Depends(get_session),
):
    """获取挑战进度"""
    challenge = await session.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    result = await session.execute(
        select(ChallengeProgress)
        .where(ChallengeProgress.challenge_id == challenge_id)
        .order_by(ChallengeProgress.day)
    )
    progress = result.scalars().all()
    return [
        {
            "day": p.day,
            "metrics": p.metrics,
            "notes": p.notes,
            "recorded_at": p.recorded_at.isoformat(),
        }
        for p in progress
    ]


@router.post("/{challenge_id}/log")
async def log_challenge_progress(
    challenge_id: int,
    day: int = Query(...),
    metrics: Optional[str] = Query(None),
    notes: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """记录挑战进度"""
    challenge = await session.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    try:
        metrics_data = json.loads(metrics) if metrics else {}
    except json.JSONDecodeError:
        metrics_data = {}

    progress = ChallengeProgress(
        challenge_id=challenge_id,
        day=day,
        metrics=metrics_data,
        notes=notes,
    )
    session.add(progress)

    # 检查是否完成
    if day >= challenge.target_days:
        challenge.status = "completed"
        from datetime import datetime
        challenge.completed_at = datetime.utcnow()

    await session.commit()
    return {"message": "Progress logged", "day": day, "status": challenge.status}


@router.get("/templates")
async def get_challenge_templates():
    """获取预置挑战模板"""
    return [
        {
            "id": "beat_market",
            "title": "Beat the Market",
            "description": "Outperform S&P 500 index over the simulation period",
            "target_days": 365,
            "constraints": {"benchmark": "SPY", "min_return_over_benchmark": 0.05},
            "reward": "Market Beater Badge"
        },
        {
            "id": "survive_crash",
            "title": "Survive a Crash",
            "description": "Maintain portfolio value during a simulated market crash",
            "target_days": 200,
            "constraints": {"crash_day_range": [100, 150], "max_drawdown": 0.15},
            "reward": "Crisis Manager Badge"
        },
        {
            "id": "double_capital",
            "title": "Double Your Capital",
            "description": "Grow your portfolio by 100% within the target period",
            "target_days": 730,
            "constraints": {"target_return": 1.0},
            "reward": "Investment Master Badge"
        },
        {
            "id": "value_investing",
            "title": "Value Investor",
            "description": "Achieve lowest average P/E ratio among peers",
            "target_days": 1000,
            "constraints": {"avg_pe_threshold": 15, "min_holdings": 5},
            "reward": "Value Investor Badge"
        },
        {
            "id": "dividend_king",
            "title": "Dividend King",
            "description": "Build a portfolio generating consistent dividend income",
            "target_days": 730,
            "constraints": {"min_dividend_yield": 0.04, "dividend_growth_years": 3},
            "reward": "Dividend King Badge"
        },
        {
            "id": "risk_adjusted",
            "title": "Risk-Adjusted Returns",
            "description": "Achieve highest Sharpe ratio among all strategies",
            "target_days": 365,
            "constraints": {"min_sharpe_ratio": 1.5},
            "reward": "Risk Manager Badge"
        },
    ]
