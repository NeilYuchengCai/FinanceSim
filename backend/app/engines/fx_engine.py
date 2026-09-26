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
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "base": self.base,
            "quote": self.quote,
            "price": round(self.price, 5),
            "spread": round(self.spread * 10000, 2),  # 转为点数
            "volatility": round(self.volatility * 100, 4),
            "change_24h": round(self._calculate_change(), 5),
            "high_24h": round(self.price * 1.002, 5),
            "low_24h": round(self.price * 0.998, 5),
        }
    
    def _calculate_change(self) -> float:
        """计算24小时变化"""
        return round(random.uniform(-0.005, 0.005), 5)
    
    def update(self, volatility_mult: float = 1.0) -> Dict:
        """更新价格"""
        old_price = self.price
        # 基于波动率的价格变动
        change = random.gauss(0, self.volatility * volatility_mult)
        self.price = max(0.001, self.price * (1 + change))
        self.last_update = datetime.now()
        
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

    def __init__(self):
        self.pairs: Dict[str, CurrencyPair] = {}
        self._pair_configs = self._load_seed_pairs()
        self.price_history: Dict[str, List[Dict]] = {t: [] for t in self._pair_configs}
        self._init_pairs()
        logger.info(f"FXEngine initialized with {len(self.pairs)} pairs")

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
            update_result = pair.update(volatility_mult)
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
    
    def get_pair(self, ticker: str) -> Optional[CurrencyPair]:
        """获取单个货币对"""
        return self.pairs.get(ticker.upper())
    
    def get_all_pairs(self) -> List[Dict]:
        """获取所有货币对"""
        return [pair.to_dict() for pair in self.pairs.values()]
    
    def get_price_history(self, ticker: str, limit: int = 100) -> List[Dict]:
        """获取历史价格"""
        ticker = ticker.upper()
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
            # 特定冲击对特定货币对的影响
            if shock_type == "central_bank" and "USD" in ticker:
                impact = random.gauss(0, multiplier * 2)
            elif shock_type == "trade_war" and "EUR" in ticker:
                impact = random.gauss(-multiplier, multiplier)
            else:
                impact = random.gauss(0, multiplier)
            
            old_price = pair.price
            pair.price = max(0.001, pair.price * (1 + impact))
            results[ticker] = {
                "impact": round(impact * 100, 4),
                "old_price": round(old_price, 5),
                "new_price": round(pair.price, 5)
            }
        
        logger.info(f"Applied shock {shock_type} with magnitude {magnitude}")
        return results
