"""
FinanceSim Routers 导出
"""
from app.routers.worlds import router as worlds_router
from app.routers.assets import router as assets_router
from app.routers.trading import router as trading_router
from app.routers.simulation import router as simulation_router
from app.routers.analytics import router as analytics_router
from app.routers.events import router as events_router
from app.routers.search import router as search_router
from app.routers.economy import router as economy_router
from app.routers.bonds import router as bonds_router
from app.routers.news import router as news_router

__all__ = [
    "worlds_router",
    "assets_router",
    "trading_router",
    "simulation_router",
    "analytics_router",
    "events_router",
    "search_router",
    "economy_router",
    "bonds_router",
    "news_router"
]
