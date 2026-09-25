"""
FinanceSim Analytics Router
分析 API
"""
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models import Asset, PriceHistory
from app.engines.analytics_engine import AnalyticsEngine

router = APIRouter(prefix="/analytics", tags=["analytics"])

analytics = AnalyticsEngine()


@router.get("/returns/{ticker}")
async def get_returns(
    ticker: str,
    world_id: int,
    period: str = Query("1y", pattern="^(1d|1w|1m|3m|6m|1y|5y|max)$"),
    session: AsyncSession = Depends(get_session)
):
    """获取收益率"""
    # 获取资产
    asset_result = await session.execute(
        select(Asset).where(Asset.world_id == world_id, Asset.ticker == ticker)
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # 获取价格历史
    result = await session.execute(
        select(PriceHistory)
        .where(PriceHistory.asset_id == asset.id)
        .order_by(PriceHistory.timestamp.asc())
    )
    prices = [p.close for p in result.scalars().all()]
    
    if len(prices) < 2:
        return {"ticker": ticker, "returns": [], "annualized_return": 0, "sharpe_ratio": 0, "max_drawdown": 0}
    
    returns = analytics.calculate_returns(prices)
    periods_map = {"1d": 252*365, "1w": 252*52, "1m": 252*12, "3m": 252*4, "6m": 252*2, "1y": 252, "5y": 252/5, "max": 252}
    periods = periods_map.get(period, 252)
    
    return {
        "ticker": ticker,
        "returns": [round(r, 6) for r in returns],
        "annualized_return": round(analytics.annualized_return(returns, periods), 6),
        "sharpe_ratio": round(analytics.sharpe_ratio(returns), 4),
        "max_drawdown": analytics.max_drawdown(prices)
    }


@router.get("/portfolio")
async def get_portfolio_analytics(
    world_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取投资组合分析"""
    # 实现投资组合分析逻辑
    return {
        "world_id": world_id,
        "metrics": {}
    }


@router.get("/correlation")
async def get_correlation(
    world_id: int,
    tickers: str = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """获取相关性矩阵"""
    ticker_list = tickers.split(",")
    
    # 获取所有相关资产的价格历史
    prices_dict = {}
    for ticker in ticker_list:
        asset_result = await session.execute(
            select(Asset).where(Asset.world_id == world_id, Asset.ticker == ticker.strip())
        )
        asset = asset_result.scalar_one_or_none()
        if asset:
            price_result = await session.execute(
                select(PriceHistory.close)
                .where(PriceHistory.asset_id == asset.id)
                .order_by(PriceHistory.timestamp.asc())
            )
            prices_dict[ticker.strip()] = [p for p in price_result.scalars().all()]
    
    if not prices_dict:
        raise HTTPException(status_code=404, detail="No assets found")
    
    matrix = analytics.correlation_matrix(prices_dict)
    
    return {
        "tickers": ticker_list,
        "matrix": [[round(v, 4) for v in row] for row in matrix]
    }
