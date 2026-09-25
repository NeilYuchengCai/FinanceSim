"""
FinanceSim News Router
新闻 API
"""
from typing import List, Optional
from fastapi import APIRouter, Query, Path

from app.engines import NewsEngine

router = APIRouter(prefix="/news", tags=["news"])

_news_engine: Optional[NewsEngine] = None


def init_news_engine(engine: NewsEngine):
    """初始化新闻引擎实例"""
    global _news_engine
    _news_engine = engine


@router.get("")
async def list_news(
    limit: int = Query(50, le=200),
    category: Optional[str] = None,
    importance: Optional[str] = None
):
    """获取新闻列表"""
    if not _news_engine:
        return {"error": "News engine not initialized"}

    # 如果没有任何新闻，先生成一些默认的
    if not _news_engine.generator.news_items:
        default_assets = [
            {"ticker": "AAPL", "name": "Apple Inc", "sector": "Technology"},
            {"ticker": "MSFT", "name": "Microsoft Corp", "sector": "Technology"},
            {"ticker": "GOOGL", "name": "Alphabet Inc", "sector": "Technology"},
            {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Finance"},
            {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
        ]
        default_macro = {
            "gdp_growth": 0.025,
            "inflation": 0.02,
            "unemployment": 0.05,
            "interest_rate": 0.05
        }
        _news_engine.generate_daily_news(default_assets, default_macro)

    return _news_engine.generator.get_news(
        limit=limit,
        category=category,
        importance=importance
    )


@router.get("/briefing")
async def get_briefing(
    hours: int = Query(24, ge=1, le=168)
):
    """获取新闻简报"""
    if not _news_engine:
        return {"error": "News engine not initialized"}
    
    return _news_engine.get_briefing(hours)


@router.get("/headlines")
async def get_headlines(
    limit: int = Query(10, le=50)
):
    """获取头条新闻"""
    if not _news_engine:
        return {"error": "News engine not initialized"}
    
    return _news_engine.get_headlines(limit)


@router.get("/daily-summary/{day_offset}")
async def get_daily_summary(
    day_offset: int = Path(..., ge=-30, le=0)
):
    """获取指定日期的新闻摘要"""
    if not _news_engine:
        return {"error": "News engine not initialized"}
    
    return _news_engine.generator.get_daily_summary(day_offset)


@router.get("/impact-summary")
async def get_impact_summary():
    """获取最新市场影响摘要"""
    if not _news_engine:
        return {"error": "News engine not initialized"}
    
    briefing = _news_engine.get_briefing(hours=24)
    return {
        "impact_summary": briefing.get("market_impact_summary", "No recent impact"),
        "sentiment_index": briefing.get("sentiment_index", 0),
        "sentiment_label": briefing.get("sentiment_label", "Neutral"),
        "breaking_count": briefing.get("breaking_count", 0),
        "total_items": briefing.get("total_items", 0)
    }


@router.post("/generate")
async def generate_news(
    force: bool = Query(False),
    days: int = Query(1, ge=1, le=30)
):
    """生成新闻（可用于测试）"""
    if not _news_engine:
        return {"error": "News engine not initialized"}
    
    # 模拟资产数据
    assets = [
        {"ticker": "AAPL", "name": "Apple Inc", "sector": "Technology"},
        {"ticker": "MSFT", "name": "Microsoft Corp", "sector": "Technology"},
        {"ticker": "GOOGL", "name": "Alphabet Inc", "sector": "Technology"},
        {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Finance"},
        {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
    ]
    
    # 模拟宏观状态
    macro_state = {
        "gdp_growth": 0.025,
        "inflation": 0.02,
        "unemployment": 0.05,
        "interest_rate": 0.05
    }
    
    news_list = []
    for _ in range(days):
        batch = _news_engine.generate_daily_news(assets, macro_state)
        news_list.extend(batch)
    
    return {
        "generated": len(news_list),
        "news": news_list[:20]  # 返回最近20条
    }
