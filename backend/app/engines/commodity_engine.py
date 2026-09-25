"""
FinanceSim Commodity Engine
负责商品市场模拟，支持能源、贵金属、农产品、工业金属
"""
import random
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CommodityConfig:
    """商品配置"""
    ticker: str
    name: str
    category: str  # ENERGY, METAL, AGRICULTURE, PRECIOUS_METAL
    subcategory: str
    baseline_price: float
    volatility: float
    contract_size: float = 1000.0
    tick_size: float = 0.01
    seasonality_factor: float = 1.0
    supply: float = 1000000.0
    demand: float = 950000.0
    inventory: float = 500000.0


class CommodityEngine:
    """商品市场引擎"""

    # 默认商品列表
    DEFAULT_COMMODITIES = {
        "CL": CommodityConfig(
            ticker="CL", name="原油 (WTI)", category="ENERGY",
            subcategory="能源", baseline_price=78.50, volatility=0.025,
            contract_size=1000.0, tick_size=0.01,
            supply=10000000.0, demand=9800000.0, inventory=3500000000.0
        ),
        "BZ": CommodityConfig(
            ticker="BZ", name="布伦特原油", category="ENERGY",
            subcategory="能源", baseline_price=82.30, volatility=0.023,
            contract_size=1000.0, tick_size=0.01,
            supply=9500000.0, demand=9200000.0, inventory=3200000000.0
        ),
        "NG": CommodityConfig(
            ticker="NG", name="天然气", category="ENERGY",
            subcategory="能源", baseline_price=2.85, volatility=0.045,
            contract_size=10000.0, tick_size=0.001,
            supply=40000.0, demand=38000.0, inventory=4200000000.0
        ),
        "GC": CommodityConfig(
            ticker="GC", name="黄金", category="PRECIOUS_METAL",
            subcategory="贵金属", baseline_price=2035.00, volatility=0.012,
            contract_size=100.0, tick_size=0.1,
            supply=5000.0, demand=4800.0, inventory=35000.0
        ),
        "SI": CommodityConfig(
            ticker="SI", name="白银", category="PRECIOUS_METAL",
            subcategory="贵金属", baseline_price=24.50, volatility=0.018,
            contract_size=5000.0, tick_size=0.005,
            supply=25000.0, demand=23000.0, inventory=80000.0
        ),
        "HG": CommodityConfig(
            ticker="HG", name="铜", category="METAL",
            subcategory="工业金属", baseline_price=3.85, volatility=0.015,
            contract_size=25000.0, tick_size=0.0005,
            supply=2000000.0, demand=1950000.0, inventory=400000.0
        ),
        "ALI": CommodityConfig(
            ticker="ALI", name="铝", category="METAL",
            subcategory="工业金属", baseline_price=2.25, volatility=0.014,
            contract_size=25000.0, tick_size=0.0025,
            supply=1800000.0, demand=1750000.0, inventory=350000.0
        ),
        "ZC": CommodityConfig(
            ticker="ZC", name="玉米", category="AGRICULTURE",
            subcategory="农产品", baseline_price=4.65, volatility=0.016,
            contract_size=5000.0, tick_size=0.0025,
            seasonality_factor=1.1,
            supply=15000000.0, demand=14500000.0, inventory=2000000000.0
        ),
        "ZW": CommodityConfig(
            ticker="ZW", name="小麦", category="AGRICULTURE",
            subcategory="农产品", baseline_price=6.15, volatility=0.018,
            contract_size=5000.0, tick_size=0.0025,
            seasonality_factor=0.9,
            supply=8000000.0, demand=7800000.0, inventory=1500000000.0
        ),
        "ZS": CommodityConfig(
            ticker="ZS", name="大豆", category="AGRICULTURE",
            subcategory="农产品", baseline_price=12.80, volatility=0.017,
            contract_size=5000.0, tick_size=0.0025,
            seasonality_factor=1.05,
            supply=4500000.0, demand=4300000.0, inventory=900000000.0
        ),
    }

    # 外部冲击类型及影响
    SHOCK_TYPES = {
        "geopolitical": {"name": "地缘政治冲突", "impact_range": (0.02, 0.08), "affected": ["CL", "BZ", "NG"]},
        "weather": {"name": "恶劣天气", "impact_range": (0.01, 0.05), "affected": ["ZC", "ZW", "ZS"]},
        "demand_shock": {"name": "需求冲击", "impact_range": (0.015, 0.04), "affected": ["CL", "HG", "ALI"]},
        "supply_disruption": {"name": "供应中断", "impact_range": (0.02, 0.06), "affected": ["CL", "NG", "SI"]},
        "dollar_strength": {"name": "美元走强", "impact_range": (-0.02, -0.005), "affected": ["GC", "SI", "HG", "ALI"]},
    }

    def __init__(self):
        self.commodities: Dict[str, Dict] = {}
        self.price_history: Dict[str, List[Dict]] = {}
        self._init_commodities()

    def _init_commodities(self):
        """初始化商品"""
        for ticker, config in self.DEFAULT_COMMODITIES.items():
            self.commodities[ticker] = {
                "config": config,
                "current_price": config.baseline_price,
                "last_update": datetime.now(),
                "supply": config.supply,
                "demand": config.demand,
                "inventory": config.inventory,
            }
            self.price_history[ticker] = []

    def step(self, volatility_mult: float = 1.0) -> Dict[str, Dict]:
        """
        推进一个时间步，更新商品价格
        Returns: 更新后的商品状态
        """
        results = {}
        for ticker, state in self.commodities.items():
            config = state["config"]
            old_price = state["current_price"]

            # 基于供需关系计算基础价格变化
            supply_demand_ratio = state["supply"] / state["demand"] if state["demand"] > 0 else 1.0
            supply_pressure = (supply_demand_ratio - 1.0) * 0.001

            # 季节性因子
            seasonal_adjustment = config.seasonality_factor - 1.0

            # 随机波动
            random_change = random.gauss(0, config.volatility * volatility_mult)

            # 综合价格变化
            total_change = random_change + supply_pressure + seasonal_adjustment * 0.0001
            new_price = max(0.001, old_price * (1 + total_change))

            state["current_price"] = new_price
            state["last_update"] = datetime.now()

            # 更新供需
            supply_shock = random.gauss(0, config.supply * 0.001)
            demand_shock = random.gauss(0, config.demand * 0.001)
            state["supply"] = max(0, state["supply"] + supply_shock)
            state["demand"] = max(0, state["demand"] + demand_shock)
            state["inventory"] = max(0, state["inventory"] + state["supply"] - state["demand"])

            # 记录历史
            self.price_history[ticker].append({
                "timestamp": state["last_update"].isoformat(),
                "open": round(old_price, 4),
                "high": round(max(old_price, new_price) * (1 + abs(random.gauss(0, config.volatility * 0.3))), 4),
                "low": round(min(old_price, new_price) * (1 - abs(random.gauss(0, config.volatility * 0.3))), 4),
                "close": round(new_price, 4),
                "volume": int(random.randint(10000, 100000)),
                "supply": round(state["supply"], 2),
                "demand": round(state["demand"], 2),
                "inventory": round(state["inventory"], 2),
            })
            # 保留最近1000条
            if len(self.price_history[ticker]) > 1000:
                self.price_history[ticker] = self.price_history[ticker][-1000:]

            results[ticker] = {
                "ticker": ticker,
                "name": config.name,
                "category": config.category,
                "old_price": round(old_price, 4),
                "new_price": round(new_price, 4),
                "change": round((new_price - old_price) / old_price, 6),
                "change_pct": round(total_change * 100, 4),
                "supply": round(state["supply"], 2),
                "demand": round(state["demand"], 2),
                "inventory": round(state["inventory"], 2),
            }

        logger.info(f"Commodity step completed, updated {len(results)} commodities")
        return results

    def get_commodity(self, ticker: str) -> Optional[Dict]:
        """获取单个商品信息"""
        state = self.commodities.get(ticker.upper())
        if not state:
            return None
        config = state["config"]
        return {
            "ticker": ticker.upper(),
            "name": config.name,
            "category": config.category,
            "subcategory": config.subcategory,
            "current_price": round(state["current_price"], 4),
            "baseline_price": config.baseline_price,
            "volatility": config.volatility,
            "contract_size": config.contract_size,
            "tick_size": config.tick_size,
            "seasonality_factor": config.seasonality_factor,
            "supply": round(state["supply"], 2),
            "demand": round(state["demand"], 2),
            "inventory": round(state["inventory"], 2),
            "last_update": state["last_update"].isoformat(),
        }

    def get_all_commodities(self) -> List[Dict]:
        """获取所有商品"""
        return [self.get_commodity(t) for t in self.commodities.keys() if self.get_commodity(t)]

    def get_price_history(self, ticker: str, limit: int = 100) -> List[Dict]:
        """获取历史价格"""
        ticker = ticker.upper()
        history = self.price_history.get(ticker, [])
        return history[-limit:]

    def apply_shock(self, shock_type: str, magnitude: float = 1.0) -> Dict:
        """
        应用外部冲击
        Args:
            shock_type: 冲击类型 (geopolitical, weather, demand_shock, supply_disruption, dollar_strength)
            magnitude: 冲击强度 (0.1 - 5.0)
        """
        shock = self.SHOCK_TYPES.get(shock_type)
        if not shock:
            return {"error": f"Unknown shock type: {shock_type}"}

        low, high = shock["impact_range"]
        base_impact = random.uniform(low, high) * magnitude
        affected = shock["affected"]

        results = {}
        for ticker in self.commodities.keys():
            if ticker in affected:
                state = self.commodities[ticker]
                old_price = state["current_price"]
                # 冲击对供需的影响
                if shock_type in ["supply_disruption", "weather"]:
                    state["supply"] *= (1 - magnitude * 0.05)
                elif shock_type == "demand_shock":
                    state["demand"] *= (1 + magnitude * 0.03)
                elif shock_type == "dollar_strength":
                    base_impact *= -1  # 美元走强，商品降价

                impact = base_impact + random.gauss(0, 0.005)
                new_price = max(0.001, old_price * (1 + impact))
                state["current_price"] = new_price
                state["last_update"] = datetime.now()

                results[ticker] = {
                    "impact": round(impact * 100, 4),
                    "old_price": round(old_price, 4),
                    "new_price": round(new_price, 4),
                }

        logger.info(f"Applied shock {shock_type} with magnitude {magnitude}")
        return results

    def get_market_summary(self) -> Dict:
        """获取市场摘要"""
        commodities = self.get_all_commodities()
        if not commodities:
            return {"total": 0, "categories": {}}

        # 按类别分组
        categories: Dict[str, List[Dict]] = {}
        for c in commodities:
            cat = c["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(c)

        summary = {
            "total": len(commodities),
            "categories": {},
            "top_gainers": [],
            "top_losers": [],
        }

        for cat, items in categories.items():
            # 计算类别平均变化
            changes = [random.uniform(-0.003, 0.003) for _ in items]  # 模拟变化
            avg_change = sum(changes) / len(changes) if changes else 0
            summary["categories"][cat] = {
                "count": len(items),
                "avg_change_pct": round(avg_change * 100, 4),
                "items": [
                    {
                        "ticker": i["ticker"],
                        "price": i["current_price"],
                        "change_pct": round(changes[idx] * 100, 4),
                    }
                    for idx, i in enumerate(items)
                ]
            }

        # 找出涨跌榜
        sorted_items = sorted(commodities, key=lambda x: random.uniform(-0.005, 0.005), reverse=True)
        summary["top_gainers"] = sorted_items[:3]
        summary["top_losers"] = sorted_items[-3:]

        return summary
