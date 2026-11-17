"""
FinanceSim Analytics Router
分析 API
"""
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_session
from app.dependencies import get_world_or_404
from app.models import Asset, PriceHistory, World
from app.engines.analytics_engine import AnalyticsEngine

router = APIRouter(prefix="/analytics", tags=["analytics"])

analytics = AnalyticsEngine()

# 每个周期对应的日线截窗长度（种子与日K均为日线；"1d" 只有 1 根K线，
# 取最近 2 根才能算出 1 个日收益率，否则返回空收益序列）。
PERIOD_WINDOW_BARS = {
    "1d": 2, "1w": 5, "1m": 21, "3m": 63, "6m": 126,
    "1y": 252, "5y": 1260, "max": None,
}
# 年化因子：收益率序列由日线算出，统一按 252 个交易日年化。
# 旧实现按 window 长度反推"每年多少期"，出现 "5y": 252/5=50.4 这类离谱值。
TRADING_DAYS_PER_YEAR = 252


@router.get("/returns/{ticker}")
async def get_returns(
    ticker: str,
    world_id: int,
    period: str = Query("1y", pattern="^(1d|1w|1m|3m|6m|1y|5y|max)$"),
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session)
):
    """获取收益率（按 period 真实截窗，年化因子统一 252）"""
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

    # 按 period 截窗（max 取全部）
    window = PERIOD_WINDOW_BARS.get(period)
    if window is not None:
        prices = prices[-window:]

    if len(prices) < 2:
        return {"ticker": ticker, "returns": [], "annualized_return": 0, "sharpe_ratio": 0, "max_drawdown": 0}

    returns = analytics.calculate_returns(prices)

    return {
        "ticker": ticker,
        "returns": [round(r, 6) for r in returns],
        "annualized_return": round(analytics.annualized_return(returns, TRADING_DAYS_PER_YEAR), 6),
        "sharpe_ratio": round(analytics.sharpe_ratio(returns), 4),
        "max_drawdown": analytics.max_drawdown(prices)
    }


@router.get("/portfolio")
async def get_portfolio_analytics(
    world_id: int = 1,
    world: World = Depends(get_world_or_404),
    session: AsyncSession = Depends(get_session),
):
    """获取投资组合分析（真实指标，来自 PortfolioEngine；引擎不可用时 503）"""
    from app.routers.trading import get_portfolio_engine

    try:
        portfolio = await get_portfolio_engine(world_id, session)
    except Exception as e:  # 引擎/数据库异常：明确失败，不返回空 metrics 假装成功
        raise HTTPException(status_code=503, detail=f"Portfolio engine unavailable: {e}")

    perf = portfolio.get_performance()
    positions = portfolio.get_all_positions()

    # 铁律②：PortfolioEngine 现返回 Decimal。/portfolio 是只读 HTTP 边界，
    # 参与除法/round 前显式转 float，避免 Decimal 与 float 混算；
    # 写入 DB 的路径仍保持 Decimal 不在此转换。
    market_value = sum(float(p["market_value"]) for p in positions)
    unrealized_pnl = sum(float(p["unrealized_pnl"]) for p in positions)
    cost_basis = sum(float(p["cost_basis"]) for p in positions)
    net_worth = float(perf.get("net_worth") or perf.get("total_value") or 0.0)
    cash = float(perf.get("cash", 0.0))
    realized_pnl = float(perf.get("total_realized_pnl", 0.0))
    total_invested = float(perf.get("total_invested", 0.0))
    total_value = float(perf.get("total_value", 0.0))

    metrics = {
        "cash": cash,
        "market_value": round(market_value, 2),
        "cost_basis": round(cost_basis, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "realized_pnl": round(realized_pnl, 2),
        "total_invested": round(total_invested, 2),
        "net_worth": round(net_worth, 2),
        "total_value": round(total_value, 2),
        "position_count": len(positions),
        "cash_weight": round(cash / net_worth, 4) if net_worth else 0.0,
        "positions": positions,
    }

    return {
        "world_id": world_id,
        "metrics": metrics,
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


@router.get("/breadth")
async def get_market_breadth(
    world_id: int = 1,
    session: AsyncSession = Depends(get_session)
):
    """市场广度概览

    完全基于 price_history 中的真实 K 线计算涨跌家数、新高/新低、涨跌幅分布、
    板块分布、主要指数以及涨幅/跌幅/成交额榜。不做任何抽样或占位返回。
    """
    asset_rows = (await session.execute(
        select(
            Asset.id, Asset.ticker, Asset.name, Asset.type,
            Asset.sector, Asset.currency, Asset.current_price, Asset.market_cap,
        ).where(Asset.world_id == world_id)
    )).all()

    meta = {}
    for aid, ticker, name, atype, sector, ccy, price, mcap in asset_rows:
        meta[aid] = {
            "ticker": ticker,
            "name": name,
            "type": atype,
            "sector": sector or "Unclassified",
            "currency": ccy,
            "price": price,
            "market_cap": mcap,
        }

    if not meta:
        return {"error": "No assets found", "total_tracked": 0}

    # 每资产最近两根 K 线，用于计算最新涨跌幅
    ranked = await session.execute(text(
        "SELECT asset_id, rn, close, volume FROM ("
        "  SELECT asset_id, close, volume,"
        "         ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY timestamp DESC) AS rn"
        "  FROM price_history"
        ") WHERE rn <= 2"
    ))
    latest, previous = {}, {}
    for aid, rn, close, vol in ranked.all():
        if aid not in meta:
            continue
        if rn == 1:
            latest[aid] = (close, vol)
        else:
            previous[aid] = close

    # 区间高低点，用于新高/新低判定
    extremes = {}
    for aid, hi, lo in (await session.execute(text(
        "SELECT asset_id, MAX(high), MIN(low) FROM price_history GROUP BY asset_id"
    ))).all():
        extremes[aid] = (hi, lo)

    buckets = {
        "below_-5": 0, "-5_to_-2": 0, "-2_to_-0.5": 0, "-0.5_to_0.5": 0,
        "0.5_to_2": 0, "2_to_5": 0, "above_5": 0,
    }

    advancing = declining = unchanged = 0
    new_highs = new_lows = 0
    change_sum = 0.0
    movers = []
    sectors = {}
    indices = []

    # 统计口径：个股与 ETF 计入广度；指数是广度本身的体现，单独列出
    BREADTH_TYPES = ("EQUITY", "ETF")

    for aid, info in meta.items():
        if aid not in latest or aid not in previous:
            continue
        last, vol = latest[aid]
        prev = previous[aid]
        if not prev or last is None:
            continue

        pct = (last - prev) / prev * 100.0
        hi, lo = extremes.get(aid, (None, None))

        is_new_high = bool(hi and last >= hi * 0.999)
        is_new_low = bool(lo and last <= lo * 1.001)

        if info["type"] == "INDEX":
            indices.append({
                "ticker": info["ticker"],
                "name": info["name"],
                "price": round(last, 2),
                "change_pct": round(pct, 3),
            })
            continue

        if info["type"] not in BREADTH_TYPES:
            continue

        change_sum += pct
        movers.append({"aid": aid, "pct": pct, "volume": vol or 0, "info": info, "price": last})

        if pct > 0.05:
            advancing += 1
        elif pct < -0.05:
            declining += 1
        else:
            unchanged += 1

        if is_new_high:
            new_highs += 1
        if is_new_low:
            new_lows += 1

        if pct < -5:
            buckets["below_-5"] += 1
        elif pct < -2:
            buckets["-5_to_-2"] += 1
        elif pct < -0.5:
            buckets["-2_to_-0.5"] += 1
        elif pct <= 0.5:
            buckets["-0.5_to_0.5"] += 1
        elif pct <= 2:
            buckets["0.5_to_2"] += 1
        elif pct <= 5:
            buckets["2_to_5"] += 1
        else:
            buckets["above_5"] += 1

        s = sectors.setdefault(info["sector"], {
            "sector": info["sector"], "count": 0,
            "change_sum": 0.0, "advancing": 0, "declining": 0,
        })
        s["count"] += 1
        s["change_sum"] += pct
        if pct > 0:
            s["advancing"] += 1
        elif pct < 0:
            s["declining"] += 1

    tracked = advancing + declining + unchanged
    sector_list = sorted(
        [
            {
                "sector": v["sector"],
                "count": v["count"],
                "avg_change_pct": round(v["change_sum"] / v["count"], 3) if v["count"] else 0.0,
                "advancing": v["advancing"],
                "declining": v["declining"],
            }
            for v in sectors.values()
        ],
        key=lambda x: -x["count"],
    )

    def top(key, reverse=True, n=5):
        ordered = sorted(movers, key=lambda m: m["pct"], reverse=reverse)[:n]
        return [
            {
                "ticker": m["info"]["ticker"],
                "name": m["info"]["name"],
                "price": round(m["price"], 2),
                "change_pct": round(m["pct"], 3),
            }
            for m in ordered
        ]

    most_active = sorted(movers, key=lambda m: m["volume"], reverse=True)[:5]

    return {
        "world_id": world_id,
        "total_tracked": tracked,
        "advancing": advancing,
        "declining": declining,
        "unchanged": unchanged,
        "advancers_pct": round(advancing / tracked * 100, 2) if tracked else 0.0,
        "decliners_pct": round(declining / tracked * 100, 2) if tracked else 0.0,
        "advance_decline_ratio": round(advancing / declining, 3) if declining else None,
        "advance_decline_line": advancing - declining,
        "new_highs": new_highs,
        "new_lows": new_lows,
        "avg_change_pct": round(change_sum / tracked, 3) if tracked else 0.0,
        "distribution": buckets,
        "sectors": sector_list,
        "indices": sorted(indices, key=lambda x: x["ticker"]),
        "gainers": top("pct", reverse=True),
        "losers": top("pct", reverse=False),
        "most_active": [
            {
                "ticker": m["info"]["ticker"],
                "name": m["info"]["name"],
                "price": round(m["price"], 2),
                "volume": int(m["volume"]),
                "change_pct": round(m["pct"], 3),
            }
            for m in most_active
        ],
        "data_source": "SIMULATED",
    }
