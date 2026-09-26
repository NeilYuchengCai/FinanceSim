"""
FinanceSim Backend Application
FastAPI 入口
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, close_db
from app.config import settings
from app.routers import worlds, assets, trading, simulation, analytics, events, search, economy, bonds, news as news_router, fx, bot, snapshots, challenges, commodities
from app.routers import realtime as realtime_router
from app.engines import EconomicEngine, BondEngine, CentralBank, NewsEngine, FXEngine, BotEngine, EventGenerator, EventPropagation, CommodityEngine
from app.services.market_stream import get_market_stream

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局引擎实例
_economic_engine: EconomicEngine = None
_central_bank: CentralBank = None
_bond_engine: BondEngine = None
_news_engine = None
_fx_engine = None
_bot_engine: BotEngine = None
_event_generator: EventGenerator = None
_event_propagation: EventPropagation = None
_commodity_engine: CommodityEngine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _economic_engine, _central_bank, _bond_engine, _news_engine, _fx_engine, _bot_engine, _event_generator, _event_propagation, _commodity_engine

    # 启动时初始化
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # 初始化经济引擎
    logger.info("Initializing Economic Engine...")
    _economic_engine = EconomicEngine()
    _central_bank = CentralBank(_economic_engine)
    economy.init_economy(_economic_engine, _central_bank)
    logger.info("Economic Engine initialized")

    # 初始化债券引擎
    logger.info("Initializing Bond Engine...")
    _bond_engine = BondEngine()
    bonds.init_bond_engine(_bond_engine)
    logger.info("Bond Engine initialized")

    # 初始化新闻引擎
    logger.info("Initializing News Engine...")
    _news_engine = NewsEngine()
    news_router.init_news_engine(_news_engine)
    logger.info("News Engine initialized")

    from app.engines import FXEngine
    _fx_engine = FXEngine()
    fx.init_fx_engine(_fx_engine)
    logger.info("FX Engine initialized")

    # 初始化 Bot 引擎
    logger.info("Initializing Bot Engine...")
    _bot_engine = BotEngine()
    bot.init_bot_engine(_bot_engine)
    logger.info("Bot Engine initialized")

    # 初始化事件引擎
    logger.info("Initializing Event Engine...")
    _event_generator = EventGenerator(1)
    _event_propagation = EventPropagation()
    events.init_event_engine(_event_generator, _event_propagation)
    logger.info("Event Engine initialized")

    # 初始化商品引擎
    logger.info("Initializing Commodity Engine...")
    _commodity_engine = CommodityEngine()
    commodities.init_commodity_engine(_commodity_engine)
    logger.info("Commodity Engine initialized")

    # 启动实时行情流：内存价格每秒小幅游走，供 /api/v1/ws/prices 推送
    logger.info("Starting market price stream...")
    await get_market_stream().start()
    logger.info("Market price stream started")

    yield

    # 关闭时清理（先停行情流，它会把最新价格批量回写后再交给 close_db）
    logger.info("Stopping market price stream...")
    await get_market_stream().stop()
    await close_db()
    logger.info("Database closed")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local Financial Market Simulation Platform",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(worlds.router, prefix=settings.API_PREFIX)
app.include_router(assets.router, prefix=settings.API_PREFIX)
app.include_router(trading.router, prefix=settings.API_PREFIX)
app.include_router(simulation.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(events.router, prefix=settings.API_PREFIX)
app.include_router(search.router, prefix=settings.API_PREFIX)
app.include_router(economy.router, prefix=settings.API_PREFIX)
app.include_router(bonds.router, prefix=settings.API_PREFIX)
app.include_router(fx.router, prefix=settings.API_PREFIX)
app.include_router(bot.router, prefix=settings.API_PREFIX)
app.include_router(snapshots.router, prefix=settings.API_PREFIX)
app.include_router(news_router.router, prefix=settings.API_PREFIX)
app.include_router(challenges.router, prefix=settings.API_PREFIX)
app.include_router(commodities.router, prefix=settings.API_PREFIX)
app.include_router(realtime_router.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
