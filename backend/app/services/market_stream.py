"""
FinanceSim 实时行情流服务

在内存中维护一份资产价格状态，按固定节奏（默认 1 秒）做**小幅**几何布朗运动，
供 WebSocket 端点推送增量行情，让前端无需切换栏目就能看到价格持续跳动。

设计要点：
1. 启动时从 assets 表加载 ticker / current_price / volatility，之后全部在内存演化。
2. 每模拟秒的波动率 = 年化波动率 / sqrt(一年秒数) * TICK_VOL_SCALE（GBM 严格时间缩放）；
   advance() 再按本 tick 覆盖的模拟秒数做 sqrt 缩放，使任意倍速下价格波动都真实，
   不会几秒内翻倍或归零，也不会因倍速加快而失真。
3. 叠加极弱的 OU 均值回复，长期运行也不会跑飞。
4. 非交易日不波动（依赖 trading_calendar，未就绪时降级为"始终交易"）。
5. 数据库只按固定间隔批量回写 current_price，不做每秒写入。
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set

from sqlalchemy import select, text

from app.core.datasource import DataSource
from app.database import async_session_factory
from app.models import Asset

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- 交易日历
# trading_calendar 由另一位同事并行开发，可能尚未落地。
# 导入失败时降级为"始终交易"，避免本模块因依赖他人而崩溃。
try:
    from app.services.trading_calendar import (
        is_trading_day as _is_trading_day,
        is_open_for as _is_open_for,
    )
except ImportError:  # pragma: no cover - 依赖未就绪时的降级分支
    _is_trading_day = None
    _is_open_for = None


# ---------------------------------------------------------------- 仿真时钟注入
# routers/simulation 在启动时把"当前世界的 SimulationClock.current_time"接进来，
# 使行情流对每类资产按真实模拟时间判定开市/休市（严格停盘）。
# 未注入时退化为 wall-clock datetime.now()，保持向后兼容。
_sim_clock_provider = None


def set_sim_clock_provider(fn) -> None:
    """注入"返回当前模拟时间(datetime)"的回调，由 routers/simulation 调用。"""
    global _sim_clock_provider
    _sim_clock_provider = fn


def get_sim_clock_time() -> datetime:
    """当前模拟时间；未注入时退回 wall-clock。"""
    if _sim_clock_provider is not None:
        return _sim_clock_provider()
    return datetime.now()


# ---------------------------------------------------------------- 仿真参数
TRADING_DAYS_PER_YEAR = 252

# 一年有多少秒（按 365.25 天计）。用于把"年化波动率"严格折算成"每秒波动率"：
#   σ_per_sec = 年化波动率 / sqrt(SECONDS_PER_YEAR)
# 这是几何布朗运动(GBM)的时间缩放律：任意时长 Δt(秒) 的价格标准差 = σ_per_sec * sqrt(Δt)。
# 因此无论模拟以何种倍速推进，价格波动都严格等价于"真实流逝的模拟秒数"——
# 倍速只改变时间流速，不改变波动的真实性，实现与现实完全贴合的全真模拟。
SECONDS_PER_YEAR = 365.25 * 24 * 3600

# 每秒波动相对"严格年化折算"的放大系数（整体调校旋钮）。
# 设为 1.0 即纯 GBM 真实波动；如需更快看到价格活动可上调（如 1.5~2.0），
# 但会偏离真实波动率，故默认保持 1.0 以求全真。
TICK_VOL_SCALE = 1.0
# 均值回复强度（OU 过程），保证长期运行价格围绕启动价波动而不是单边跑飞
MEAN_REVERSION = 0.00005
# 单个 tick 允许的最大相对变动，兜底防止极端随机数造成跳变
MAX_TICK_MOVE = 0.02

# 休市（周末/节假日）时是否仍然推进价格。
# 默认 True：本平台是仿真，"随时都在丝滑跳动"是核心体验，休市完全静止会被当成功能坏了。
# 改为 False 即严格遵循交易日历：休市期间只发空帧（连接存活，但价格不动）。
TICK_WHEN_MARKET_CLOSED = True
# 休市期间的波动缩放：流动性低，波动收敛
OFF_SESSION_VOL_SCALE = 0.35

# ---------------- 价格过程拟真：跳变（肥尾）与波动率聚集 ----------------
# 个股级 Poisson 跳变：全年约发生 JUMPS_PER_YEAR 次，每次跳幅为对数正态 N(0, JUMP_SIGMA)，
# 制造真实市场的"肥尾"——绝大多数 tick 小幅游走，偶发跳空。概率随本 tick 模拟秒数线性缩放。
JUMPS_PER_YEAR = 3.0
JUMP_SIGMA = 0.04
# 波动率聚集（vol clustering）：跳变/事件冲击后短期波动率抬升，随后缓慢衰减回常态，
# 与真实市场"波动聚集"特征一致（GARCH 直觉）。
JUMP_VOL_BOOST = 2.0        # 发生跳变时 vol_mult 瞬时乘子
VOL_CLUSTER_DECAY = 0.03    # 每模拟秒 vol_mult 向 1.0 衰减的比例
VOL_CAP_MULT = 6.0          # vol_mult 上限，防止极端累积
# 行业因子联动强度：同一 sector 内资产额外共享一个同向因子，制造行业联动
RHO_SECTOR = 0.25

# 价格推进间隔（秒）与数据库批量回写间隔（秒）
TICK_INTERVAL = 1.0
PERSIST_INTERVAL = 30.0
# 交易日历判断结果的缓存时长（秒）
TRADING_CACHE_SECONDS = 60.0

# 订阅者队列容量：客户端慢时丢弃最旧的一帧，保证推的是最新价
SUB_QUEUE_SIZE = 8

# 缺 volatility 时的按类型默认值（年化）
DEFAULT_VOLATILITY = {
    "EQUITY": 0.25,
    "ETF": 0.18,
    "INDEX": 0.15,
    "FX": 0.08,
    "BOND": 0.05,
}
VOL_FLOOR = 0.01
VOL_CAP = 2.0
PRICE_FLOOR = 0.01


def _utc_iso() -> str:
    """生成形如 2026-09-26T01:00:00 的时间戳字符串。"""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def _decimals_for(asset_type: str, price: float) -> int:
    """按资产类型/价位决定展示小数位：外汇与低价标的需要更多精度。"""
    if (asset_type or "").upper() == "FX" or price < 1:
        return 4
    return 2


class _AssetState:
    """单个资产的内存状态。"""

    __slots__ = ("asset_id", "ticker", "price", "anchor", "prev_close",
                 "sigma", "decimals", "last_sent", "asset_type", "name", "sector",
                 "exchange", "prev_day_close", "data_source",
                 "beta", "vol_mult", "cum_factor")

    def __init__(self, asset_id: int, ticker: str, price: float, anchor: float,
                 prev_close: float, sigma: float, decimals: int,
                 asset_type: str = "", name: str = "", sector: str = "",
                 exchange: str = "", prev_day_close: float = 0.0,
                 beta: float = 1.0):
        self.asset_id = asset_id
        self.ticker = ticker
        self.price = price
        self.anchor = anchor
        self.prev_close = prev_close
        self.sigma = sigma
        self.decimals = decimals
        self.last_sent: Optional[float] = None
        self.asset_type = asset_type
        self.name = name or ticker
        self.sector = sector
        self.exchange = exchange or ""
        # 波动率聚集乘子：均值回复到 1.0；事件/大跳会瞬时抬升，随后缓慢衰减
        self.vol_mult = 1.0
        # 关联因子累积冲击：事件以"因子"形式一次性注入，advance 每 tick 逐步吸收
        self.cum_factor = 0.0
        self.beta = beta if beta is not None else 1.0
        # 上一个模拟交易日收盘（由 record_daily_bar 维护），用于计算"当日涨跌幅"
        self.prev_day_close = prev_day_close
        # 价格来源标记：默认 SIMULATED，外部行情接入后可标为 LIVE
        self.data_source: str = DataSource.SIMULATED.value

    def change_pct(self, price: float) -> float:
        if self.prev_close and self.prev_close > 0:
            return (price - self.prev_close) / self.prev_close * 100.0
        return 0.0

    def daily_change_pct(self) -> float:
        """相对上一个模拟交易日收盘的涨跌幅，用于新闻与市场叙事。

        未记录过日K时退化为累计涨跌幅（种子 prev_close），避免新模拟首日新闻出现 0% 静止。
        """
        if self.prev_day_close and self.prev_day_close > 0:
            return (self.price - self.prev_day_close) / self.prev_day_close * 100.0
        return self.change_pct(self.price)

    def to_item(self) -> dict:
        price = round(self.price, self.decimals)
        self.last_sent = price
        return {"t": self.ticker, "p": price, "c": round(self.change_pct(price), 2)}

    def to_full(self) -> dict:
        """扩展快照：供新闻引擎等需要名称/板块/类型的消费者使用。"""
        price = round(self.price, self.decimals)
        return {
            "t": self.ticker, "p": price, "c": round(self.change_pct(price), 2),
            "n": self.name, "s": self.sector, "y": self.asset_type,
            "d": round(self.daily_change_pct(), 2),
            "ds": self.data_source,
        }


class MarketStream:
    """内存价格状态机 + WebSocket 广播。"""

    def __init__(self, tick_interval: float = TICK_INTERVAL,
                 persist_interval: float = PERSIST_INTERVAL,
                 seed: Optional[int] = None):
        self.tick_interval = tick_interval
        self.persist_interval = persist_interval
        self._assets: Dict[str, _AssetState] = {}
        self._subscribers: Set["asyncio.Queue[dict]"] = set()
        self._tick_task: Optional[asyncio.Task] = None
        self._persist_task: Optional[asyncio.Task] = None
        # 外部行情播种任务（启动后在后台异步跑，绝不阻塞端口绑定 / 服务器就绪）
        self._live_seed_task: Optional[asyncio.Task] = None
        self._running = False
        # 实例级随机源：同一 seed 下价格游走序列可复现（restore/重放一致）
        self._rng = random.Random(seed)
        # 模拟暂停回调：由 routers/simulation 注入，返回当前 world 的
        # SimulationClock.is_paused。返回 True 时本循环冻结价格演进（只发心跳）。
        self._paused_provider: Optional[Callable[[], bool]] = None
        # 当前每 tick 覆盖的模拟秒数（来自 SimulationClock 的倍速档位）。
        # 默认 1.0（实时）；行情波动按 sqrt(本值) 缩放，使任意倍速下波动都真实。
        self._sim_seconds_per_tick: float = 1.0

    # ------------------------------------------------------------ 生命周期
    async def start(self) -> None:
        if self._running:
            return
        await self.load()
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop(), name="market-stream-tick")
        self._persist_task = asyncio.create_task(self._persist_loop(), name="market-stream-persist")
        # 可选外部行情接入（OFFLINE-FIRST）：在后台异步播种真实报价，绝不阻塞启动。
        # 服务器先以合成价立即就绪；播种成功则价格翻 LIVE，失败（无网/限流）则静默保留合成价。
        try:
            from app.config import settings
            if settings.USE_EXTERNAL_DATA:
                self._live_seed_task = asyncio.create_task(
                    self._maybe_seed_live_prices(self._assets),
                    name="market-stream-live-seed",
                )
        except Exception:  # 配置缺失也不影响启动
            pass
        logger.info("Market stream started with %d instruments", len(self._assets))

    async def reseed_live_prices(self) -> int:
        """运行时手动触发一次外部真实价格重播种（设置页开启外部数据后调用）。

        仅当 ``USE_EXTERNAL_DATA`` 为真且行情流已加载资产时生效；失败静默返回 0。
        返回成功更新的资产数（0 表示未执行/失败）。
        """
        if not self._assets:
            return 0
        from app.config import settings

        if not settings.USE_EXTERNAL_DATA:
            return 0
        try:
            before = {t: st.price for t, st in self._assets.items()}
            await self._maybe_seed_live_prices(self._assets)
            updated = sum(
                1 for t, st in self._assets.items() if st.price != before.get(t)
            )
            logger.info("Live price reseed applied to %d instruments", updated)
            return updated
        except Exception as exc:  # 绝不影响主流程
            logger.warning("Live reseed failed: %s", exc)
            return 0

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        tasks = [t for t in (self._tick_task, self._persist_task) if t is not None]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tick_task = None
        self._persist_task = None
        if self._live_seed_task is not None:
            self._live_seed_task.cancel()
            self._live_seed_task = None
        self._subscribers.clear()
        # 退出前把最新价格落库，保证重启后价格是持续演化的
        try:
            await self.persist()
        except Exception:  # pragma: no cover - 关闭路径上的兜底
            logger.exception("Failed to flush prices on shutdown")
        logger.info("Market stream stopped")

    # ------------------------------------------------------------ 暂停联动
    def set_pause_provider(self, provider: "Callable[[], bool]") -> None:
        """注册"模拟是否暂停"的查询回调，使行情流在模拟暂停时冻结价格推进。

        由 routers/simulation 注入（读取各自 world 的 SimulationClock.is_paused）。
        回调抛异常时行情流按"未暂停"处理，避免回调故障导致行情长期被冻结。
        """
        self._paused_provider = provider

    # ------------------------------------------------------------ 倍速联动
    def set_sim_seconds_per_tick(self, sim_seconds: float) -> None:
        """告诉行情流当前每 tick 推进多少模拟秒（由 SimulationClock 的倍速档位驱动）。

        行情波动按 sqrt(模拟秒数) 缩放：本 tick 覆盖 S 模拟秒时，
        标准差 = σ_per_sec * sqrt(S)，严格等价于"真实流逝 S 秒"的 GBM 演化。
        这样倍速只改变时间流速而不改变波动真实性 —— 任意倍速下都是全真模拟。
        默认 1.0（实时）。传入非法值退化为 1.0，保证行情流不崩。
        """
        try:
            value = float(sim_seconds)
            self._sim_seconds_per_tick = value if value > 0 else 1.0
        except (TypeError, ValueError):
            self._sim_seconds_per_tick = 1.0

    def get_sim_seconds_per_tick(self) -> float:
        """读取当前每 tick 模拟秒数（供 /step 快进前暂存、结束后还原）。"""
        return self._sim_seconds_per_tick

    # ------------------------------------------------------------ 加载
    async def load(self) -> None:
        async with async_session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        Asset.id,
                        Asset.ticker,
                        Asset.type,
                        Asset.current_price,
                        Asset.volatility,
                        Asset.name,
                        Asset.sector,
                        Asset.exchange,
                        Asset.beta,
                    ).where(Asset.current_price.isnot(None), Asset.current_price > 0)
                )
            ).all()

        if not rows:
            logger.warning("No assets with current_price found, market stream stays empty")
            return

        prev_closes = await self._load_prev_closes([int(r[0]) for r in rows])
        # 上一个模拟交易日的收盘（最新一根 K 线的收盘），用于重启后也能算出"当日涨跌幅"
        last_closes = await self._load_last_closes([int(r[0]) for r in rows])

        states: Dict[str, _AssetState] = {}
        for asset_id, ticker, asset_type, price, volatility, name, sector, exchange, beta in rows:
            price = float(price)
            asset_type = (asset_type or "").upper()
            vol = float(volatility) if volatility else 0.0
            if vol <= 0:
                vol = DEFAULT_VOLATILITY.get(asset_type, 0.2)
            vol = min(max(vol, VOL_FLOOR), VOL_CAP)

            # 每模拟秒的波动率：年化波动率 / sqrt(一年秒数)，再乘放大系数。
            # advance() 会再按本 tick 覆盖的模拟秒数做 sqrt 缩放，保证任意倍速都真实。
            sigma = vol / math.sqrt(SECONDS_PER_YEAR) * TICK_VOL_SCALE

            prev_close = prev_closes.get(int(asset_id))
            if prev_close is None or prev_close <= 0:
                prev_close = price

            states[ticker] = _AssetState(
                asset_id=int(asset_id),
                ticker=ticker,
                price=price,
                anchor=price,
                prev_close=prev_close,
                sigma=sigma,
                decimals=_decimals_for(asset_type, price),
                asset_type=asset_type,
                name=name or ticker,
                sector=sector or "",
                exchange=exchange or "",
                prev_day_close=last_closes.get(int(asset_id)) or 0.0,
                beta=float(beta) if beta is not None else 1.0,
            )

        self._assets = states
        # 注意：可选外部行情播种已移出 load()，改由 start() 在后台异步执行，
        # 以避免 217 只资产的实时报价请求阻塞服务器启动（OFFLINE-FIRST：启动不可用外部数据阻塞）。

    async def _maybe_seed_live_prices(self, states: Dict[str, "_AssetState"]) -> None:
        """用外部价格 provider 给内存状态播种真实报价（防御性、可选）。"""
        if not states:
            return
        try:
            from app.config import settings
            if not settings.USE_EXTERNAL_DATA:
                return
            from app.data.providers import get_provider, maybe_fetch

            price_provider = get_provider("alpha_vantage")
            if price_provider is None or not price_provider.enabled:
                return

            tickers = [st.ticker for st in states.values()]
            quotes = await maybe_fetch(price_provider, symbols=tickers)
            if not quotes:
                return

            updated = 0
            for ticker, st in states.items():
                q = quotes.get(ticker)
                if not isinstance(q, dict):
                    continue
                price = q.get("price")
                if price is None:
                    continue
                try:
                    price = float(price)
                except (TypeError, ValueError):
                    continue
                if price <= 0:
                    continue
                st.price = price
                st.anchor = price  # 让后续 GBM 围绕真实价波动，而不是直接跳回种子价
                st.data_source = DataSource.LIVE.value
                updated += 1
            if updated:
                logger.info(
                    "Seeded %d live prices from %s (rest remain SIMULATED)",
                    updated, price_provider.name,
                )
        except Exception as exc:  # 绝不允许外部数据影响启动
            logger.warning("External price seeding failed, keeping synthetic prices: %s", exc)

    def add_asset(self, asset: "Asset") -> None:
        """运行时把新建资产注册进行情流，使其可立即定价/交易/推送（无需重启）。

        仅在行情流已加载（_assets 非空）时生效；若尚未 start 则跳过，保持健壮。
        参数 asset 为已提交、含 id 的 Asset ORM 实例。
        """
        if not self._assets:
            return
        asset_id = int(getattr(asset, "id", 0))
        ticker = getattr(asset, "ticker", None)
        if not ticker:
            return
        price = getattr(asset, "current_price", None)
        if price is None or float(price) <= 0:
            return
        price = float(price)
        asset_type = (getattr(asset, "type", "") or "").upper()
        vol = float(getattr(asset, "volatility", 0) or 0)
        if vol <= 0:
            vol = DEFAULT_VOLATILITY.get(asset_type, 0.2)
        vol = min(max(vol, VOL_FLOOR), VOL_CAP)
        sigma = vol / math.sqrt(SECONDS_PER_YEAR) * TICK_VOL_SCALE
        self._assets[ticker] = _AssetState(
            asset_id=asset_id,
            ticker=ticker,
            price=price,
            anchor=price,
            prev_close=price,
            sigma=sigma,
            decimals=_decimals_for(asset_type, price),
            asset_type=asset_type,
            name=getattr(asset, "name", None) or ticker,
            sector=getattr(asset, "sector", None) or "",
            exchange=getattr(asset, "exchange", None) or "",
            prev_day_close=0.0,
            beta=float(getattr(asset, "beta", None) or 1.0),
        )

    async def _load_prev_closes(self, asset_ids: List[int]) -> Dict[int, float]:
        """取每个资产上一根 K 线的收盘价作为"前收"，与 assets 列表接口口径一致。

        取不到时返回空字典，调用方会退化为用当前价，涨跌幅从 0 开始演化。
        """
        if not asset_ids:
            return {}
        ids = ",".join(str(int(i)) for i in asset_ids)
        try:
            async with async_session_factory() as session:
                rows = (
                    await session.execute(
                        text(
                            "SELECT asset_id, rn, close FROM ("
                            "  SELECT asset_id, close,"
                            "         ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY timestamp DESC) AS rn"
                            f"  FROM price_history WHERE asset_id IN ({ids})"
                            ") WHERE rn <= 2"
                        )
                    )
                ).fetchall()
        except Exception:
            logger.exception("Failed to load previous closes, falling back to current price")
            return {}

        bars: Dict[int, Dict[int, float]] = {}
        for asset_id, rn, close in rows:
            if close is None:
                continue
            bars.setdefault(int(asset_id), {})[int(rn)] = float(close)

        out: Dict[int, float] = {}
        for asset_id, seq in bars.items():
            # rn=2 才是"上一根"，只有一根 K 线时退化为该根本身
            prev = seq.get(2, seq.get(1))
            if prev and prev > 0:
                out[asset_id] = prev
        return out

    async def _load_last_closes(self, asset_ids: List[int]) -> Dict[int, float]:
        """取每个资产最新一根 K 线的收盘价，作为"上一模拟交易日收盘"。

        用于重启后仍能算出有意义的当日涨跌幅（而非退化成累计涨跌幅）。
        """
        if not asset_ids:
            return {}
        ids = ",".join(str(int(i)) for i in asset_ids)
        try:
            async with async_session_factory() as session:
                rows = (
                    await session.execute(
                        text(
                            "SELECT asset_id, rn, close FROM ("
                            "  SELECT asset_id, close,"
                            "         ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY timestamp DESC) AS rn"
                            f"  FROM price_history WHERE asset_id IN ({ids})"
                            ") WHERE rn <= 1"
                        )
                    )
                ).fetchall()
        except Exception:
            logger.exception("Failed to load last closes, falling back to zero")
            return {}

        out: Dict[int, float] = {}
        for asset_id, rn, close in rows:
            if close and close > 0:
                out[int(asset_id)] = float(close)
        return out

    # ------------------------------------------------------------ 推进
    def _is_open_for(self, asset_type: str, exchange: str = "") -> bool:
        """某资产当前是否开市（严格停盘判定）。

        - trading_calendar 未就绪（导入失败）时，降级为"始终开市"，保持旧行为；
        - 否则按资产类别 + 交易所 + 当前模拟时间判定（外汇/商品 7×24 仅周末休市，
          股票类按各自交易所独立日历错峰开收）。
        任何异常都按"开市"处理，避免行情被长期冻结。
        """
        if _is_open_for is None:
            return True
        try:
            return bool(_is_open_for(asset_type, get_sim_clock_time(), exchange or None))
        except Exception as exc:
            logger.warning("trading_calendar check failed (%s), falling back to open", exc)
            return True

    def advance(self) -> List[dict]:
        """推进一个 tick，返回本次**发生变化**的条目。

        价格过程拟真（全真模拟核心）：
        1. 跨资产相关性：引入**单市场因子 + 行业因子 + 特异因子**三因子模型。
           每 tick 生成一个全市场共享的 market_z 与每个行业共享的 sector_z，
           各资产收益 = β·market_z + β_s·sector_z + 特异_z。同一因子被所有相关
           资产共享，从而全市场/同行业自然同向联动，且每个资产**边际波动率仍等于
           其自身 sigma**（权重按 ρ 分解，方差守恒），不会因加因子而失真。
        2. 跳变（肥尾）：个股按 Poisson 过程偶发跳空，跳幅对数正态。
        3. 波动率聚集：每资产维护 vol_mult，事件/跳变后瞬时抬升并缓慢衰减回 1.0。
        4. 严格停盘：每个资产按其自身交易所日历决定演进/冻结；债券由 BondEngine 驱动跳过。
        5. 倍速守恒：所有扩散项按 √(模拟秒数) 缩放，均值回复按线性缩放，任意倍速下等价真实流逝。
        """
        if not self._assets:
            return []

        # 本 tick 覆盖的模拟秒数（由倍速档位决定）。方差线性叠加 => 标准差按 √(秒数) 缩放。
        sim_sec = self._sim_seconds_per_tick if self._sim_seconds_per_tick > 0 else 1.0
        sec_factor = math.sqrt(sim_sec)

        # 共享因子：一个全市场 z，一个各行业 z（行业因子在同行业内制造额外联动）。
        # 均为标准正态，缩放交由各资产自身的 σ 与权重完成，保证边际方差守恒。
        market_z = self._rng.gauss(0.0, 1.0)
        sector_z: Dict[str, float] = {}
        # 个股级 Poisson 跳变概率（随模拟秒数线性缩放）
        jump_prob = JUMPS_PER_YEAR * sim_sec / SECONDS_PER_YEAR

        items: List[dict] = []
        for state in self._assets.values():
            # 严格停盘：该资产对应市场休市时——若允许休市续tick则降波动演进，否则冻结。
            open_now = self._is_open_for(state.asset_type, state.exchange)
            if not open_now:
                if not TICK_WHEN_MARKET_CLOSED:
                    continue
                vol_scale = OFF_SESSION_VOL_SCALE
            else:
                vol_scale = 1.0
            # 债券由 BondEngine 权威驱动，行情流跳过其 GBM
            if state.asset_type == "BOND":
                continue

            # 波动率聚集：vol_mult 向 1.0 缓慢衰减（事件/跳变会先抬升它）
            if state.vol_mult > 1.0:
                state.vol_mult += (1.0 - state.vol_mult) * VOL_CLUSTER_DECAY * sim_sec
                if state.vol_mult < 1.0:
                    state.vol_mult = 1.0
            elif state.vol_mult < 1.0:
                state.vol_mult = 1.0

            # 三因子权重分解（方差守恒：w_m^2 + w_s^2 + w_i^2 = 1）
            beta = state.beta if state.beta else 1.0
            # 市场相关度 ρ_m 随 beta 增大（beta 越大越随大盘走）
            rho_m = max(0.1, min(0.85, 0.15 + 0.25 * min(abs(beta), 2.0)))
            w_m = math.sqrt(rho_m)
            residual = math.sqrt(1.0 - rho_m)
            # 行业因子仅在"该资产有 sector 且市场里存在同业"时生效；
            # 这里恒定给一个小的行业联动权重，制造行业板块共振
            rho_s = RHO_SECTOR
            w_s = residual * math.sqrt(rho_s)
            w_i = residual * math.sqrt(1.0 - rho_s)
            sec = state.sector or "Unknown"
            if sec not in sector_z:
                sector_z[sec] = self._rng.gauss(0.0, 1.0)
            z_s = sector_z[sec]
            z_i = self._rng.gauss(0.0, 1.0)

            sigma_i = state.sigma * state.vol_mult * vol_scale
            pull = -MEAN_REVERSION * sim_sec * math.log(state.price / state.anchor)
            diffusion = sigma_i * sec_factor * (w_m * market_z + w_s * z_s + w_i * z_i)
            # 对数收益 = 均值回复力 + 扩散 - 0.5σ²（GBM 漂移修正）
            log_ret = pull + diffusion - 0.5 * (sigma_i * sec_factor) ** 2

            # 个股级 Poisson 跳变（肥尾）
            if self._rng.random() < jump_prob:
                jump = self._rng.gauss(0.0, JUMP_SIGMA)
                log_ret += jump
                # 跳变后波动率聚集抬升
                state.vol_mult = min(VOL_CAP_MULT, state.vol_mult * JUMP_VOL_BOOST)

            log_ret = max(-MAX_TICK_MOVE, min(MAX_TICK_MOVE, log_ret))

            new_price = max(state.price * math.exp(log_ret), PRICE_FLOOR)
            rounded = round(new_price, state.decimals)
            state.price = new_price

            if state.last_sent is not None and abs(rounded - state.last_sent) < 10 ** -state.decimals / 2:
                continue
            state.last_sent = rounded
            items.append({"t": state.ticker, "p": rounded,
                          "c": round(state.change_pct(rounded), 2)})
        return items

    def update_price(self, ticker: str, price: float) -> bool:
        """外部权威源（如 BondEngine 步进后）回灌某资产的最新价。

        用于把债券的权威定价写入行情流，使交易/前端/快照拿到的是最新价。
        返回是否命中并更新成功。
        """
        state = self._assets.get(ticker)
        if state is None:
            return False
        state.price = max(float(price), PRICE_FLOOR)
        return True

    async def _tick_loop(self) -> None:
        while self._running:
            # 模拟暂停时冻结价格演进：只发心跳帧保持连接，不再推进行情。
            # 这样"时间没动，市场也不会浮动"——行情与模拟时钟严格同步。
            paused = False
            if self._paused_provider is not None:
                try:
                    paused = bool(self._paused_provider())
                except Exception:
                    # 回调故障按"未暂停"处理，避免行情被长期冻结
                    paused = False
            if paused:
                self._broadcast({"type": "heartbeat", "ts": _utc_iso(), "items": [], "paused": True})
                await asyncio.sleep(self.tick_interval)
                continue
            try:
                items = self.advance()
                # 每 tick 都发一帧：有变化就带 items，休市时 items 为空，
                # 对端据此既能拿到增量也能判断连接存活。
                # 带上 paused 标志，使前端能实时反映"模拟已暂停"状态。
                self._broadcast({"type": "update", "ts": _utc_iso(), "items": items, "paused": False})
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Market stream tick failed")
            await asyncio.sleep(self.tick_interval)

    # ------------------------------------------------------------ 订阅
    def subscribe(self) -> "asyncio.Queue[dict]":
        queue: "asyncio.Queue[dict]" = asyncio.Queue(maxsize=SUB_QUEUE_SIZE)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: "asyncio.Queue[dict]") -> None:
        self._subscribers.discard(queue)

    def snapshot_items(self) -> List[dict]:
        """全量快照。"""
        return [state.to_item() for state in self._assets.values()]

    def snapshot_full(self) -> List[dict]:
        """扩展快照：含名称/板块/类型，供新闻引擎等消费。"""
        return [state.to_full() for state in self._assets.values()]

    async def record_daily_bar(self, day: int, timestamp: datetime) -> int:
        """把当前内存价格固化为一根日 K 线写入 price_history。

        这样模拟时间跨天推进时，价格历史会持续增长，Analytics 等依赖
        price_history 的页面就能跟随模拟时间延伸到"当天"，而不是停在种子数据的最后一天。

        open 取上一日收盘(prev_close)，close 取当前实时价，high/low 在两者基础上微展；
        仅对 EQUITY/ETF/INDEX 写入（与种子脚本的 HISTORY_TYPES 保持一致）。
        写入前先按 world_day 删除已有 bar，保证重复调用幂等。
        """
        from app.database import async_session_factory
        from sqlalchemy import text as sa_text

        HISTORY_TYPES = ("EQUITY", "ETF", "INDEX")
        bar_rows = []
        for st in self._assets.values():
            atype = (st.asset_type or "").upper()
            if atype not in HISTORY_TYPES:
                continue
            # 开盘取"上一个模拟交易日收盘"，使日K的 open 连续演化而非卡在种子初值
            open_px = (
                st.prev_day_close
                if st.prev_day_close and st.prev_day_close > 0
                else (st.prev_close if st.prev_close and st.prev_close > 0 else st.price)
            )
            close_px = st.price
            # 当日高低在开收两端外扩一点，制造真实感
            ext = self._rng.uniform(0.002, 0.015)
            high_px = max(open_px, close_px) * (1.0 + ext)
            low_px = min(open_px, close_px) * (1.0 - ext)
            vol = int(self._rng.uniform(200_000, 8_000_000))
            bar_rows.append({
                "asset_id": st.asset_id,
                "timestamp": timestamp,
                "open": round(open_px, st.decimals),
                "high": round(high_px, st.decimals),
                "low": round(low_px, st.decimals),
                "close": round(close_px, st.decimals),
                "volume": vol,
                "world_day": day,
            })
            # 记录本交易日收盘，供下一交易日新闻计算"当日涨跌幅"
            st.prev_day_close = close_px

        if not bar_rows:
            return 0

        async with async_session_factory() as session:
            # 幂等：先清掉同一模拟日已有的 bar
            await session.execute(
                sa_text("DELETE FROM price_history WHERE world_day = :day"),
                {"day": day},
            )
            await session.execute(
                sa_text(
                "INSERT INTO price_history "
                "(asset_id, timestamp, open, high, low, close, volume, world_day, data_source) "
                f"VALUES (:asset_id, :timestamp, :open, :high, :low, :close, :volume, :world_day, '{DataSource.SIMULATED.value}')"
                ),
                bar_rows,
            )
            await session.commit()
        return len(bar_rows)

    def set_price(self, ticker: str, price: float) -> bool:
        """恢复指定资产的价格（用于存档加载）。"""
        state = self._assets.get(ticker)
        if state is None:
            return False
        state.price = max(float(price), PRICE_FLOOR)
        return True

    def apply_shock(self, ticker: str, pct: float) -> None:
        """对指定资产施加一次性价格冲击（事件影响），pct 为小数（如 -0.05 表示 -5%）。

        用于把"市场事件"真实反映到行情上，使时间线与价格走势紧密联动。
        同时瞬时抬升该资产波动率乘子，触发**波动率聚集**（事件后短期波动放大、缓慢回落）。
        """
        state = self._assets.get(ticker)
        if state is None or not pct:
            return
        new_price = max(state.price * (1.0 + float(pct)), PRICE_FLOOR)
        state.price = new_price
        boost = 1.0 + min(abs(pct), 0.1) * 8.0
        state.vol_mult = min(VOL_CAP_MULT, state.vol_mult * boost)

    def apply_shocks(self, shocks: Dict[str, float]) -> int:
        """批量施加相关性冲击（事件引擎调用）。

        参数 shocks: {ticker: pct}，pct 为小数。逐个调用 apply_shock。
        返回实际命中并施加的资产数量。
        """
        applied = 0
        for ticker, pct in shocks.items():
            before = self._assets.get(ticker)
            if before is None:
                continue
            self.apply_shock(ticker, pct)
            applied += 1
        return applied

    def _broadcast(self, payload: dict) -> None:
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:  # pragma: no cover - 极端竞态
                pass

    # ------------------------------------------------------------ 落库
    async def persist(self) -> None:
        """批量回写 assets.current_price（一次事务，不做逐行写入）。"""
        if not self._assets:
            return
        payload = [
            {"asset_id": state.asset_id, "price": round(state.price, state.decimals)}
            for state in self._assets.values()
        ]
        async with async_session_factory() as session:
            await session.execute(
                text("UPDATE assets SET current_price = :price WHERE id = :asset_id"),
                payload,
            )
            await session.commit()

    async def _persist_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.persist_interval)
            try:
                await self.persist()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Failed to persist streamed prices")


_stream: Optional[MarketStream] = None


def get_market_stream(seed: Optional[int] = None) -> MarketStream:
    """进程内单例。

    seed 仅在首次创建时生效（用于按世界种子复现价格演化）；
    单例已存在时返回既有实例，忽略后续 seed 参数。
    """
    global _stream
    if _stream is None:
        _stream = MarketStream(seed=seed)
    return _stream
