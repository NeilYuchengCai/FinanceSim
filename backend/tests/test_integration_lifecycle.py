"""
FinanceSim 集成测试：覆盖"建世界 -> 建资产 -> 启动模拟 -> 市价单成交 -> 查持仓"
的完整生命周期，并验证两个体验质量修复：
  1) 新世界启动后即处于可交易状态（market_status == OPEN），市价单不再被 400「市场休市」劝退；
  2) 多个只读端点的 world_id 现在可缺省（默认世界 1），不再 422。
另含 trading_calendar.next_trading_open 的纯函数单测。

为保证可重复、不依赖共享的 financesim.db（避免与实时服务/其它测试竞争 SQLite 锁），
本模块使用独立的临时数据库，自包含、幂等。
"""
import asyncio
import os
import tempfile

import pytest

# 在导入任何 app 代码之前，确保外部数据源总开关关闭（离线优先，避免测试触碰网络）。
os.environ.setdefault("USE_EXTERNAL_DATA", "False")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.database as dbmod  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.trading_calendar import (  # noqa: E402
    MARKET_OPEN,
    market_status,
    next_trading_open,
)


def _make_isolated_db():
    """创建一个临时 SQLite 库并重建表，返回 (engine, session_factory, db_path)。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    url = f"sqlite+aiosqlite:///{tmp.name}"
    engine = create_async_engine(url, future=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return engine, factory, tmp.name


@pytest.fixture(scope="module")
def client():
    # 隔离 DB：用临时 sqlite 文件，避免与共享 financesim.db（及可能并存的实时服务）竞争锁。
    engine, factory, db_path = _make_isolated_db()
    # 把全局引擎/会话工厂替换为临时库（lifespan 的 init_db / get_session 均读取这些模块级对象）。
    dbmod.engine = engine
    dbmod.async_session_factory = factory
    try:
        with TestClient(app) as c:
            yield c
    finally:
        asyncio.run(engine.dispose())
        try:
            os.unlink(db_path)
        except OSError:
            pass


# ---------------------------------------------------------------- 纯函数单测
class TestNextTradingOpen:
    """next_trading_open：把任意时刻对齐到下一个交易时段开盘(09:30)。"""

    def test_already_open_returns_same(self):
        from datetime import datetime
        dt = datetime(2026, 11, 17, 10, 30)
        assert market_status(dt) == MARKET_OPEN
        assert next_trading_open(dt) == dt

    def test_pre_open_same_day(self):
        from datetime import datetime
        dt = datetime(2026, 11, 18, 4, 11)
        res = next_trading_open(dt)
        assert (res.year, res.month, res.day) == (2026, 11, 18)
        assert (res.hour, res.minute) == (9, 30)

    def test_weekend_rolls_to_monday(self):
        from datetime import datetime
        dt = datetime(2027, 2, 6, 0, 0)  # 周六
        res = next_trading_open(dt)
        assert res.weekday() == 0  # 周一
        assert (res.hour, res.minute) == (9, 30)

    def test_after_close_rolls_next_day(self):
        from datetime import datetime
        dt = datetime(2026, 11, 20, 16, 30)  # 周五盘后
        res = next_trading_open(dt)
        assert res.weekday() == 0  # 跳过周末到周一
        assert (res.hour, res.minute) == (9, 30)


# ---------------------------------------------------------------- 生命周期集成
import uuid  # noqa: E402


def _uniq():
    return "QA" + uuid.uuid4().hex[:10].upper()


def test_world_lifecycle_is_tradable_on_start(client: TestClient):
    """核心体验修复：新世界启动后市场 OPEN，市价买单能成交。"""
    wname = _uniq()
    r = client.post("/api/v1/worlds", json={
        "name": wname,
        "mode": "simulation",
        "starting_capital": 500000.0,
        "seed": wname,
        "simulation_speed": 1.0,
        "difficulty": "normal",
    })
    assert r.status_code == 200, r.text
    wid = r.json()["id"]

    ticker = _uniq()
    r = client.post(f"/api/v1/assets?world_id={wid}", json={
        "ticker": ticker,
        "type": "EQUITY",
        "name": "QA Test Co",
        "currency": "USD",
        "price": 100.0,
    })
    assert r.status_code == 200, r.text
    assert r.json()["ticker"] == ticker

    r = client.post(f"/api/v1/simulation/{wid}/start")
    assert r.status_code == 200, r.text

    r = client.get(f"/api/v1/simulation/{wid}/status")
    assert r.status_code == 200, r.text
    status = r.json()
    assert status["market_status"] == MARKET_OPEN, status
    assert status["is_trading_day"] is True

    r = client.post(f"/api/v1/trading/orders?world_id={wid}", json={
        "asset_ticker": ticker,
        "side": "BUY",
        "type": "MARKET",
        "quantity": 10,
    })
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["status"] == "FILLED", order
    assert order["filled_quantity"] == 10

    r = client.get(f"/api/v1/trading/portfolio/positions?world_id={wid}")
    assert r.status_code == 200, r.text
    positions = r.json()
    assert isinstance(positions, list) and len(positions) >= 1
    assert ticker in {p["ticker"] for p in positions}


def test_world_id_defaulting_on_read_endpoints(client: TestClient):
    """world_id 缺省时回退到默认世界(1)，不再 422。

    隔离 DB 中首个被创建的世界即为 id=1；即便其它测试已先建世界，world 1 也必然存在，
    因此缺省回退路径可被稳定验证。
    """
    # 确保默认世界存在
    client.post("/api/v1/worlds", json={
        "name": _uniq(), "mode": "simulation", "starting_capital": 100000.0,
    })
    for path in ["/assets?limit=3", "/trading/portfolio", "/trading/portfolio/positions",
                "/analytics/portfolio"]:
        r = client.get(f"/api/v1{path}")
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:120]}"
