"""
FinanceSim 实时行情流服务

在内存中维护一份资产价格状态，按固定节奏（默认 1 秒）做**小幅**几何布朗运动，
供 WebSocket 端点推送增量行情，让前端无需切换栏目就能看到价格持续跳动。

设计要点：
1. 启动时从 assets 表加载 ticker / current_price / volatility，之后全部在内存演化。
2. 每 tick 的波动率 = 年化波动率 / sqrt(252) / sqrt(每交易日 tick 数) * TICK_VOL_SCALE，
   量级远小于日线，价格不会几秒内翻倍或归零。
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
from typing import Dict, List, Optional, Set

from sqlalchemy import select, text

from app.database import async_session_factory
from app.models import Asset

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- 交易日历
# trading_calendar 由另一位同事并行开发，可能尚未落地。
# 导入失败时降级为"始终交易"，避免本模块因依赖他人而崩溃。
try:
    from app.services.trading_calendar import is_trading_day as _is_trading_day
except ImportError:  # pragma: no cover - 依赖未就绪时的降级分支
    _is_trading_day = None


# ---------------------------------------------------------------- 仿真参数
TRADING_DAYS_PER_YEAR = 252

# 一个模拟交易日压缩成多少个 tick（tick 间隔默认 1 秒）
TICKS_PER_TRADING_DAY = 3600
# 每秒波动相对"日波动 / sqrt(每交易日 tick 数)"的放大系数。
# 2.0 时：年化波动 25% 的股票每秒 σ≈0.05%，178 美元的股票每秒跳动约 9 分钱，
# 一小时累计波动约 3%，肉眼可见但不夸张。
TICK_VOL_SCALE = 2.0
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
                 "prev_day_close")

    def __init__(self, asset_id: int, ticker: str, price: float, anchor: float,
                 prev_close: float, sigma: float, decimals: int,
                 asset_type: str = "", name: str = "", sector: str = "",
                 prev_day_close: float = 0.0):
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
        # 上一个模拟交易日收盘（由 record_daily_bar 维护），用于计算"当日涨跌幅"
        self.prev_day_close = prev_day_close

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
        }


class MarketStream:
    """内存价格状态机 + WebSocket 广播。"""

    def __init__(self, tick_interval: float = TICK_INTERVAL,
                 persist_interval: float = PERSIST_INTERVAL):
        self.tick_interval = tick_interval
        self.persist_interval = persist_interval
        self._assets: Dict[str, _AssetState] = {}
        self._subscribers: Set["asyncio.Queue[dict]"] = set()
        self._tick_task: Optional[asyncio.Task] = None
        self._persist_task: Optional[asyncio.Task] = None
        self._running = False
        self._trading_cache: tuple[float, bool] = (0.0, True)

    # ------------------------------------------------------------ 生命周期
    async def start(self) -> None:
        if self._running:
            return
        await self.load()
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop(), name="market-stream-tick")
        self._persist_task = asyncio.create_task(self._persist_loop(), name="market-stream-persist")
        logger.info("Market stream started with %d instruments", len(self._assets))

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
        self._subscribers.clear()
        # 退出前把最新价格落库，保证重启后价格是持续演化的
        try:
            await self.persist()
        except Exception:  # pragma: no cover - 关闭路径上的兜底
            logger.exception("Failed to flush prices on shutdown")
        logger.info("Market stream stopped")

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
        for asset_id, ticker, asset_type, price, volatility, name, sector in rows:
            price = float(price)
            asset_type = (asset_type or "").upper()
            vol = float(volatility) if volatility else 0.0
            if vol <= 0:
                vol = DEFAULT_VOLATILITY.get(asset_type, 0.2)
            vol = min(max(vol, VOL_FLOOR), VOL_CAP)

            # 每 tick 的波动率：日波动 / sqrt(每交易日 tick 数) * 放大系数
            sigma = vol / math.sqrt(TRADING_DAYS_PER_YEAR) \
                / math.sqrt(TICKS_PER_TRADING_DAY) * TICK_VOL_SCALE

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
                prev_day_close=last_closes.get(int(asset_id)) or 0.0,
            )

        self._assets = states

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
    def _is_trading_now(self) -> bool:
        if _is_trading_day is None:
            return True
        now = time.monotonic()
        cached_at, cached_value = self._trading_cache
        if now - cached_at < TRADING_CACHE_SECONDS:
            return cached_value
        value = True
        try:
            try:
                value = bool(_is_trading_day(datetime.now()))
            except TypeError:
                value = bool(_is_trading_day(datetime.now().date()))
        except Exception as exc:
            logger.warning("trading_calendar unavailable (%s), falling back to always-trading", exc)
            value = True
        self._trading_cache = (now, value)
        return value

    def advance(self) -> List[dict]:
        """推进一个 tick，返回本次**发生变化**的条目。"""
        if not self._assets:
            return []

        trading = self._is_trading_now()
        if not trading and not TICK_WHEN_MARKET_CLOSED:
            return []
        vol_scale = 1.0 if trading else OFF_SESSION_VOL_SCALE

        items: List[dict] = []
        for state in self._assets.values():
            # 几何布朗运动 + 极弱均值回复
            sigma = state.sigma * vol_scale
            pull = -MEAN_REVERSION * math.log(state.price / state.anchor)
            move = pull + sigma * random.gauss(0.0, 1.0) - 0.5 * sigma ** 2
            move = max(-MAX_TICK_MOVE, min(MAX_TICK_MOVE, move))

            new_price = max(state.price * math.exp(move), PRICE_FLOOR)
            rounded = round(new_price, state.decimals)
            state.price = new_price

            if state.last_sent is not None and abs(rounded - state.last_sent) < 10 ** -state.decimals / 2:
                continue
            state.last_sent = rounded
            items.append({"t": state.ticker, "p": rounded,
                          "c": round(state.change_pct(rounded), 2)})
        return items

    async def _tick_loop(self) -> None:
        while self._running:
            try:
                items = self.advance()
                # 每 tick 都发一帧：有变化就带 items，休市时 items 为空，
                # 对端据此既能拿到增量也能判断连接存活。
                self._broadcast({"type": "update", "ts": _utc_iso(), "items": items})
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
            ext = random.uniform(0.002, 0.015)
            high_px = max(open_px, close_px) * (1.0 + ext)
            low_px = min(open_px, close_px) * (1.0 - ext)
            vol = int(random.uniform(200_000, 8_000_000))
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
                    "VALUES (:asset_id, :timestamp, :open, :high, :low, :close, :volume, :world_day, 'simulated')"
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
        """
        state = self._assets.get(ticker)
        if state is None or not pct:
            return
        new_price = max(state.price * (1.0 + float(pct)), PRICE_FLOOR)
        state.price = new_price

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


def get_market_stream() -> MarketStream:
    """进程内单例。"""
    global _stream
    if _stream is None:
        _stream = MarketStream()
    return _stream
