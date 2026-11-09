"""
FinanceSim FX Engine
负责外汇市场模拟
"""
import random
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from app.core.datasource import DataSource, normalize_data_source

logger = logging.getLogger(__name__)


@dataclass
class CurrencyPair:
    """货币对"""
    base: str
    quote: str
    ticker: str
    price: float
    spread: float = 0.0001  # 点差
    volatility: float = 0.0002  # 日波动率
    pip: float = 0.0001  # 最小价格变动
    last_update: datetime = field(default_factory=datetime.now)
    # 当日开盘/最高/最低：随 advance/step 真实演化，替代此前的 price*1.002 硬编码
    day_open: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0

    def __post_init__(self):
        if self.day_open <= 0:
            self.day_open = self.price
        if self.day_high <= 0:
            self.day_high = self.price
        if self.day_low <= 0:
            self.day_low = self.price

    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "base": self.base,
            "quote": self.quote,
            "price": round(self.price, 5),
            "spread": round(self.spread * 10000, 2),  # 转为点数
            "volatility": round(self.volatility * 100, 4),
            "change_24h": round(self._calculate_change(), 5),
            "high_24h": round(self.day_high, 5),
            "low_24h": round(self.day_low, 5),
            # 数据来源标注：汇率全部为模拟引擎生成
            "data_source": DataSource.SIMULATED.value,
        }

    def _calculate_change(self) -> float:
        """计算24小时变化：相对当日开盘价的真实涨跌幅。"""
        if self.day_open and self.day_open > 0:
            return (self.price - self.day_open) / self.day_open
        return 0.0

    def update(self, volatility_mult: float = 1.0, rng: "random.Random" = None) -> Dict:
        """更新价格。

        rng 由调用方（FXEngine）传入可复现随机源；缺省退化为全局 random（兼容旧调用）。
        """
        old_price = self.price
        # 基于波动率的价格变动（使用传入的可复现随机源，铁律⑤）
        rng = rng or random
        change = rng.gauss(0, self.volatility * volatility_mult)
        self.price = max(0.001, self.price * (1 + change))
        self.last_update = datetime.now()
        # 维护当日高低点（必须包含当前价）
        self.day_high = max(self.day_high, self.price)
        self.day_low = min(self.day_low, self.price)

        return {
            "ticker": self.ticker,
            "old_price": round(old_price, 5),
            "new_price": round(self.price, 5),
            "change": round((self.price - old_price) / old_price, 6),
            "change_pct": round(change * 100, 4)
        }


class FXEngine:
    """外汇市场引擎"""
    
    # 主要货币对初始价格（当种子文件不可用时的兜底）
    DEFAULT_PAIRS = {
        "EUR/USD": {"base": "EUR", "quote": "USD", "price": 1.0850},
        "GBP/USD": {"base": "GBP", "quote": "USD", "price": 1.2650},
        "USD/JPY": {"base": "USD", "quote": "JPY", "price": 151.50},
        "USD/CHF": {"base": "USD", "quote": "CHF", "price": 0.8850},
        "AUD/USD": {"base": "AUD", "quote": "USD", "price": 0.6550},
        "USD/CAD": {"base": "USD", "quote": "CAD", "price": 1.3650},
        "NZD/USD": {"base": "NZD", "quote": "USD", "price": 0.6050},
        "USD/CNY": {"base": "USD", "quote": "CNY", "price": 7.2400},
    }

    @staticmethod
    def _load_seed_pairs() -> Dict[str, dict]:
        """从资产种子数据加载货币对。

        真实交易所覆盖主要货币对、交叉盘和新兴市场货币对，种子文件缺失时
        回退到内置的 8 个主要货币对。
        """
        import json
        import os

        seed = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "seed", "fx_pairs.json",
        )
        if not os.path.exists(seed):
            logger.warning("fx_pairs seed not found, falling back to DEFAULT_PAIRS")
            return dict(FXEngine.DEFAULT_PAIRS)

        try:
            with open(seed, encoding="utf-8") as f:
                rows = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read fx seed ({e}), using DEFAULT_PAIRS")
            return dict(FXEngine.DEFAULT_PAIRS)

        pairs = {}
        for r in rows:
            base = (r.get("fundamentals") or {}).get("base")
            quote = (r.get("fundamentals") or {}).get("quote")
            price = r.get("current_price")
            ticker = r.get("ticker")
            if not (base and quote and price and ticker):
                continue
            pairs[ticker] = {
                "base": base,
                "quote": quote,
                "price": float(price),
                # 外汇日波动按不同 pair 区分：主要货币对波动小，新兴市场大
                "volatility": float(r.get("volatility") or 0.0065),
            }
        return pairs or dict(FXEngine.DEFAULT_PAIRS)

    def __init__(self, seed: Optional[int] = None, world_id: Optional[int] = None):
        self.pairs: Dict[str, CurrencyPair] = {}
        self._pair_configs = self._load_seed_pairs()
        self.price_history: Dict[str, List[Dict]] = {t: [] for t in self._pair_configs}
        # 实例级可复现随机源：同一 seed 下外汇演化序列可复现（铁律⑤）
        self._seed = seed
        self._world_id = world_id
        self._rng = random.Random(seed)
        self._init_pairs()
        logger.info("FXEngine initialized with %d pairs (seed=%s)", len(self.pairs), seed)

    def _init_pairs(self):
        """初始化货币对"""
        for ticker, config in self._pair_configs.items():
            self.pairs[ticker] = CurrencyPair(
                base=config["base"],
                quote=config["quote"],
                ticker=ticker,
                price=config["price"],
                volatility=config.get("volatility", 0.0002),
            )
    
    def step(self, volatility_mult: float = 1.0) -> Dict[str, Dict]:
        """
        推进一个时间步，更新所有货币对价格
        Returns: 更新的货币对信息
        """
        results = {}
        for ticker, pair in self.pairs.items():
            update_result = pair.update(volatility_mult, self._rng)
            results[ticker] = update_result
            
            # 记录历史
            self.price_history[ticker].append({
                "timestamp": pair.last_update.isoformat(),
                "price": pair.price
            })
            # 保留最近1000条
            if len(self.price_history[ticker]) > 1000:
                self.price_history[ticker] = self.price_history[ticker][-1000:]
        
        logger.info(f"FX step completed, updated {len(results)} pairs")
        return results
    
    @staticmethod
    def normalize_ticker(ticker: str) -> str:
        """把路径参数归一化为引擎 key 形式（BASE/QUOTE）。

        路径参数不能包含 "/"，前端传 'EURUSD' / 'eur-usd'，而引擎 key 是
        'EUR/USD'；这里统一为：去空白、大写、'-'→'/'，6 位无分隔时按 3/3 插入。
        """
        t = (ticker or "").strip().upper().replace("-", "/").replace(" ", "")
        compact = t.replace("/", "")
        if len(compact) == 6:
            return f"{compact[:3]}/{compact[3:]}"
        return t or compact

    def get_pair(self, ticker: str) -> Optional[CurrencyPair]:
        """获取单个货币对"""
        return self.pairs.get(self.normalize_ticker(ticker))
    
    def get_all_pairs(self) -> List[Dict]:
        """获取所有货币对"""
        return [pair.to_dict() for pair in self.pairs.values()]

    def get_usd_rates(self) -> Dict[str, float]:
        """返回以 USD 为基准的汇率表：rate[X] = 1 单位 X 等于多少 USD。

        前端据此把任意币种金额换算到用户选中的展示货币（USD 枢纽交叉汇率）。
        规则：
        - ticker 形如 BASE/QUOTE，price = 每 1 BASE 可换多少 QUOTE。
        - 若 quote == "USD"：rate[base] = price（price 即 USD/base）。
        - 若 base  == "USD"：rate[quote] = 1/price（price 即 quote/USD → USD/quote）。
        - 第二遍用已知汇率补全交叉盘（如 EUR/GBP）能推导的币种。
        """
        rates: Dict[str, float] = {"USD": 1.0}
        for pair in self.pairs.values():
            base, quote, price = pair.base, pair.quote, pair.price
            if price <= 0:
                continue
            if quote == "USD":
                rates.setdefault(base, price)
            elif base == "USD":
                rates.setdefault(quote, 1.0 / price)

        # 第二遍：用已知汇率补全交叉盘能推导的币种（USD 枢纽）
        for pair in self.pairs.values():
            base, quote, price = pair.base, pair.quote, pair.price
            if price <= 0 or base == quote:
                continue
            if base in rates and quote not in rates:
                # price = quote per base → USD per quote = USD per base / price
                rates.setdefault(quote, rates[base] / price)
            elif quote in rates and base not in rates:
                rates.setdefault(base, rates[quote] * price)

        # 数据正确性：缺失的展示货币绝不能静默给 1.0（会让转换器按"不变"错误换算），
        # 必须显式报错，由上层端点转成 400，提示上游种子/汇率数据不完整。
        missing = [c for c in ("EUR", "CNY", "CHF", "GBP", "JPY") if c not in rates]
        if missing:
            logger.warning(
                "FX get_usd_rates: unresolved display currencies %s; refusing silent 1.0 fallback",
                missing,
            )
            raise ValueError(f"FX rate unavailable for: {', '.join(missing)}")
        return rates

    def get_price_history(self, ticker: str, limit: int = 100) -> List[Dict]:
        """获取历史价格"""
        ticker = self.normalize_ticker(ticker)
        history = self.price_history.get(ticker, [])
        return history[-limit:]
    
    def get_briefing(self) -> Dict:
        """生成外汇市场简报"""
        pairs = self.get_all_pairs()
        
        # 找出最大涨跌
        max_gain = max(pairs, key=lambda x: x["change_24h"]) if pairs else None
        max_loss = min(pairs, key=lambda x: x["change_24h"]) if pairs else None
        
        return {
            "total_pairs": len(pairs),
            "avg_volatility": sum(p["volatility"] for p in pairs) / len(pairs) if pairs else 0,
            "strongest": max_gain["ticker"] if max_gain else None,
            "weakest": max_loss["ticker"] if max_loss else None,
            "pairs": pairs
        }
    
    def apply_shock(self, shock_type: str, magnitude: float = 1.0) -> Dict:
        """
        应用外部冲击
        
        Args:
            shock_type: "central_bank" | "crisis" | "trade_war" | "pandemic"
            magnitude: 冲击强度 (0.1 - 5.0)
        """
        shock_multipliers = {
            "central_bank": 0.002,  # 央行干预
            "crisis": 0.01,         # 危机
            "trade_war": 0.005,     # 贸易战
            "pandemic": 0.008,      # 疫情
        }
        
        multiplier = shock_multipliers.get(shock_type, 0.002) * magnitude
        
        results = {}
        for ticker, pair in self.pairs.items():
            # 特定冲击对特定货币对的影响（统一走 self._rng，铁律⑤）
            if shock_type == "central_bank" and "USD" in ticker:
                impact = self._rng.gauss(0, multiplier * 2)
            elif shock_type == "trade_war" and "EUR" in ticker:
                impact = self._rng.gauss(-multiplier, multiplier)
            else:
                impact = self._rng.gauss(0, multiplier)
            
            old_price = pair.price
            pair.price = max(0.001, pair.price * (1 + impact))
            # 冲击同样计入当日高低点
            pair.day_high = max(pair.day_high, pair.price)
            pair.day_low = min(pair.day_low, pair.price)
            results[ticker] = {
                "impact": round(impact * 100, 4),
                "old_price": round(old_price, 5),
                "new_price": round(pair.price, 5)
            }
        
        logger.info("Applied shock %s with magnitude %s", shock_type, magnitude)
        return results

    async def restore_prices(self) -> None:
        """重启恢复：从 assets 表读取 FX 资产的最新价（此前由行情流 / 上轮落库写入），

        覆盖 fx_pairs.json 的静态种子价，使 FXEngine 重启后从演化后的价格继续，
        而不是退回静态种子价（铁律③ Offline-First）。同时把最近的价格历史回灌到
        内存 price_history，使 /fx/pair/{ticker}/history 重启后也有数据。
        """
        try:
            from app.database import async_session_factory
            from app.models import Asset, PriceHistory
            from sqlalchemy import select

            async with async_session_factory() as session:
                rows = (
                    await session.execute(
                        select(Asset.id, Asset.ticker, Asset.current_price)
                        .where(Asset.type == "FX")
                    )
                ).all()
                id_map = {t: (aid, cp) for aid, t, cp in rows}

                for ticker, pair in self.pairs.items():
                    rec = id_map.get(ticker)
                    if not rec:
                        continue
                    aid, cp = rec
                    if cp is not None and cp > 0:
                        pair.price = float(cp)
                        pair.day_open = pair.price
                        pair.day_high = pair.price
                        pair.day_low = pair.price
                        pair.last_update = datetime.now()
                    # 回灌最近 200 根 K 线到内存（重启后历史可见）
                    hist = (
                        await session.execute(
                            select(PriceHistory)
                            .where(PriceHistory.asset_id == aid)
                            .order_by(PriceHistory.timestamp.desc())
                            .limit(200)
                        )
                    ).scalars().all()
                    bars = list(reversed(list(hist)))  # 升序
                    self.price_history[ticker] = [
                        {
                            "timestamp": (h.timestamp.isoformat() if h.timestamp else None),
                            "open": h.open,
                            "high": h.high,
                            "low": h.low,
                            "close": h.close,
                            "volume": h.volume,
                        }
                        for h in bars
                    ]
                    # 优先用 FXEngine 自己落库的最新 bar 收盘价恢复价格（可复现、不受
                    # 行情流独立演化影响）；无 bar 时退回 assets.current_price（行情流上轮
                    # 落库值），再退回种子默认价。
                    if bars:
                        pair.price = float(bars[-1].close)
                    elif cp is not None and cp > 0:
                        pair.price = float(cp)
                    pair.day_open = pair.price
                    pair.day_high = pair.price
                    pair.day_low = pair.price
                    pair.last_update = datetime.now()
            logger.info("FXEngine restored prices/history from assets table")
        except Exception as exc:  # 防御性兜底：恢复失败时退回种子默认价
            logger.warning("FXEngine restore_prices failed, using seed defaults: %s", exc)

    async def persist_prices(self) -> None:
        """把外汇价格演化结果落库（与 MarketStream 对齐的单一真相源）。

        写两处：
        1) assets.current_price —— 重启恢复的主路径（restore_prices 读这里）；
        2) price_history —— 统一价格历史，使 /fx/pair/{ticker}/history 有连续记录。
        金额统一用 Decimal 规整后再落 Float 列，避免浮点误差累积。
        """
        try:
            from app.database import async_session_factory
            from app.models import Asset, PriceHistory
            from sqlalchemy import select, text

            async with async_session_factory() as session:
                rows = (
                    await session.execute(
                        select(Asset.id, Asset.ticker).where(Asset.type == "FX")
                    )
                ).all()
                id_map = {t: aid for aid, t in rows}

                ts = datetime.now()
                price_payload = []
                hist_payload = []
                for ticker, pair in self.pairs.items():
                    aid = id_map.get(ticker)
                    if aid is None:
                        continue
                    close = float(Decimal(str(round(pair.price, 5))))
                    day_open = float(Decimal(str(round(pair.day_open or pair.price, 5))))
                    day_high = float(Decimal(str(round(pair.day_high or pair.price, 5))))
                    day_low = float(Decimal(str(round(pair.day_low or pair.price, 5))))
                    price_payload.append({"aid": int(aid), "price": close})
                    hist_payload.append({
                        "asset_id": int(aid),
                        "timestamp": ts,
                        "open": day_open,
                        "high": day_high,
                        "low": day_low,
                        "close": close,
                        "volume": 0,
                        "world_day": None,
                        "data_source": normalize_data_source(DataSource.SIMULATED.value),
                    })

                if price_payload:
                    await session.execute(
                        text("UPDATE assets SET current_price = :price WHERE id = :aid"),
                        price_payload,
                    )
                if hist_payload:
                    await session.execute(
                        text(
                            "INSERT INTO price_history "
                            "(asset_id, timestamp, open, high, low, close, volume, world_day, data_source) "
                            "VALUES (:asset_id, :timestamp, :open, :high, :low, :close, :volume, :world_day, :data_source)"
                        ),
                        hist_payload,
                    )
                await session.commit()
            logger.info("FXEngine persisted %d pairs to assets/price_history", len(price_payload))
        except Exception as exc:  # 落库失败不应让价格演化失败
            logger.warning("FXEngine persist_prices failed: %s", exc)
