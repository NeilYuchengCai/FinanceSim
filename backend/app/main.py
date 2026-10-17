"""
FinanceSim Backend Application
FastAPI 入口
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, close_db, async_session_factory
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

    # 世界种子 -> 引擎随机源：默认世界（id=1）的 seed 经 crc32 转为整数，
    # 注入事件/商品/行情流，使同一世界的模拟演化跨重启可复现；
    # 取不到世界或 seed 时退化为固定默认值（仍然确定）。
    sim_seed = 42
    try:
        from sqlalchemy import select as _select
        from app.models import World as _World
        import zlib
        async with async_session_factory() as _seed_session:
            _world = (await _seed_session.execute(
                _select(_World).where(_World.id == 1)
            )).scalar_one_or_none()
            if _world is not None and _world.seed:
                sim_seed = zlib.crc32(str(_world.seed).encode("utf-8"))
                logger.info("World seed '%s' -> engine seed %d", _world.seed, sim_seed)
    except Exception as e:
        logger.warning(f"Failed to resolve world seed, using default {sim_seed}: {e}")

    # 每个引擎独立 try/except：单个引擎初始化失败只置 None + 记录日志，
    # 服务继续启动（路由层 503 分支接住），不再一损俱损。

    # 初始化经济引擎
    logger.info("Initializing Economic Engine...")
    try:
        _economic_engine = EconomicEngine()
        _central_bank = CentralBank(_economic_engine)
        economy.init_economy(_economic_engine, _central_bank)
        logger.info("Economic Engine initialized")
    except Exception as e:
        _economic_engine = None
        _central_bank = None
        logger.exception(f"Economic Engine init failed: {e}")

    # 初始化债券引擎
    logger.info("Initializing Bond Engine...")
    try:
        _bond_engine = BondEngine()
        bonds.init_bond_engine(_bond_engine)
        logger.info("Bond Engine initialized")
    except Exception as e:
        _bond_engine = None
        logger.exception(f"Bond Engine init failed: {e}")

    # 初始化新闻引擎
    logger.info("Initializing News Engine...")
    try:
        _news_engine = NewsEngine()
        news_router.init_news_engine(_news_engine)
        logger.info("News Engine initialized")
    except Exception as e:
        _news_engine = None
        logger.exception(f"News Engine init failed: {e}")

    logger.info("Initializing FX Engine...")
    try:
        _fx_engine = FXEngine()
        fx.init_fx_engine(_fx_engine)
        logger.info("FX Engine initialized")
    except Exception as e:
        _fx_engine = None
        logger.exception(f"FX Engine init failed: {e}")

    # 初始化 Bot 引擎
    logger.info("Initializing Bot Engine...")
    try:
        _bot_engine = BotEngine()
        bot.init_bot_engine(_bot_engine)
        logger.info("Bot Engine initialized")
    except Exception as e:
        _bot_engine = None
        logger.exception(f"Bot Engine init failed: {e}")

    # 预置几个默认 AI 交易员，让市场一开始就有人工智能活动
    if _bot_engine is not None:
        try:
            from app.engines import BotConfig
            for cfg in [
                BotConfig(name="Momentum-1", strategy="momentum", capital=100000.0, risk_tolerance=0.6),
                BotConfig(name="MeanRev-1", strategy="mean_reversion", capital=100000.0, risk_tolerance=0.4),
                BotConfig(name="MarketMaker-1", strategy="market_making", capital=200000.0, risk_tolerance=0.3),
                BotConfig(name="Macro-1", strategy="macro", capital=150000.0, risk_tolerance=0.5),
            ]:
                _bot_engine.add_bot(cfg)
            logger.info("Seeded %d default bots", len(_bot_engine.bots))
        except Exception as e:
            logger.warning(f"Failed to seed default bots: {e}")

    # 初始化事件引擎
    logger.info("Initializing Event Engine...")
    try:
        _event_generator = EventGenerator(1, seed=sim_seed)
        _event_propagation = EventPropagation()
        events.init_event_engine(_event_generator, _event_propagation)
        logger.info("Event Engine initialized")
    except Exception as e:
        _event_generator = None
        _event_propagation = None
        logger.exception(f"Event Engine init failed: {e}")

    # 初始化商品引擎
    logger.info("Initializing Commodity Engine...")
    try:
        _commodity_engine = CommodityEngine(seed=sim_seed)
        commodities.init_commodity_engine(_commodity_engine)
        logger.info("Commodity Engine initialized")
    except Exception as e:
        _commodity_engine = None
        logger.exception(f"Commodity Engine init failed: {e}")

    # 启动实时行情流：内存价格每秒小幅游走，供 /api/v1/ws/prices 推送
    logger.info("Starting market price stream...")
    try:
        await get_market_stream(seed=sim_seed).start()
        logger.info("Market price stream started")
    except Exception as e:
        logger.exception(f"Market price stream failed to start: {e}")

    yield

    # 关闭时清理（先停行情流，它会把最新价格批量回写后再交给 close_db）
    logger.info("Stopping market price stream...")
    try:
        await get_market_stream().stop()
    except Exception as e:
        logger.warning(f"Market price stream stop failed: {e}")
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
