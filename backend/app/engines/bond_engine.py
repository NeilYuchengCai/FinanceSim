"""
FinanceSim Bond Engine
负责债券定价和收益曲线
"""
import math
import logging
import json
import os
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class Bond:
    """债券模型"""
    bond_id: str
    ticker: str
    name: str
    bond_type: str  # GOVERNMENT, CORPORATE, MUNICIPAL
    coupon_rate: float  # 票面利率
    face_value: float = 1000.0
    maturity_date: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=365*10))
    issue_date: datetime = field(default_factory=datetime.now)
    credit_rating: str = "AAA"
    yield_to_maturity: float = 0.0
    price: float = 1000.0
    duration: float = 0.0
    convexity: float = 0.0
    spread: float = 0.0  # 信用利差
    
    # 状态
    remaining_days: int = 0
    accrued_interest: float = 0.0
    next_coupon_date: datetime = field(default_factory=datetime.now)
    
    def update(self, market_yield: float, risk_free_rate: Optional[float] = None):
        """根据市场收益率更新价格和久期。

        risk_free_rate 为无风险利率（取自经济引擎 interest_rate）；
        缺省时退化为 5% 的保守假设。spread = 市场收益率 - 无风险利率。
        """
        rf = 0.05 if risk_free_rate is None else float(risk_free_rate)
        # 先设置remaining_days，因为duration计算依赖它
        self.remaining_days = (self.maturity_date - datetime.now()).days
        self.yield_to_maturity = market_yield
        self.price = self._calculate_price(market_yield)
        self.duration = self._calculate_duration(market_yield)
        self.convexity = self._calculate_convexity(market_yield)
        self.spread = market_yield - rf
    
    def _calculate_price(self, ytm: float) -> float:
        """计算债券价格"""
        if ytm <= 0:
            return self.face_value
        
        # 简化计算：假设半年付息
        periods = self.remaining_days / 182.5
        coupon_payment = self.coupon_rate * self.face_value / 2
        discount_factor = 1 + ytm / 2
        
        price = 0
        for i in range(1, int(periods) + 1):
            price += coupon_payment / (discount_factor ** i)
        
        # 加上本金现值
        price += self.face_value / (discount_factor ** periods)
        
        return price
    
    def _calculate_duration(self, ytm: float) -> float:
        """计算麦考利久期 - 修正版"""
        remaining_days = self.remaining_days
        if remaining_days <= 0:
            return 0.0
        
        # 简化计算：久期约等于到期时间的一定比例
        # 对于平价债券，久期 ≈ 到期时间 * (1 + y/2) / (y * ((1+y/2)^n - 1) + y/2 + 2)
        years = remaining_days / 365.0
        if years <= 0:
            return 0.0
        
        coupon = self.coupon_rate
        y = ytm if ytm > 0 else 0.05
        
        # 修正公式：麦考利久期的简化近似
        # 对于coupon bond: Macaulay Duration ≈ n * (1+y) / (y * ((1+y)^n - 1) + y + 2)
        # 其中 n 是期数，y 是每期收益率
        
        periods = max(2, int(years * 2))  # 至少2期
        period_y = y / 2  # 每期收益率
        
        numerator = (1 + period_y)
        denominator = period_y * ((1 + period_y) ** periods - 1) + period_y + 2
        
        duration = periods * numerator / (2 * denominator)
        
        return max(0.5, min(duration, years))
    
    def _calculate_convexity(self, ytm: float) -> float:
        """计算凸性"""
        if ytm <= 0:
            return 0
        
        delta_y = 0.0001
        price_up = self._calculate_price(ytm + delta_y)
        price_down = self._calculate_price(ytm - delta_y)
        
        convexity = (price_up + price_down - 2 * self.price) / (self.price * delta_y ** 2)
        return convexity / 100  # 转换为年化
    
    def get_change(self, ytm_change: float) -> Dict:
        """计算收益率变化对价格的影响"""
        duration_effect = -self.duration * ytm_change
        convexity_effect = 0.5 * self.convexity * ytm_change ** 2
        total_change = duration_effect + convexity_effect
        
        return {
            "price_change_pct": total_change * 100,
            "duration_effect": duration_effect * 100,
            "convexity_effect": convexity_effect * 100,
            "new_price": self.price * (1 + total_change)
        }
    
    def to_dict(self) -> Dict:
        return {
            "bond_id": self.bond_id,
            "ticker": self.ticker,
            "name": self.name,
            "type": self.bond_type,
            "coupon_rate": self.coupon_rate,
            "face_value": self.face_value,
            "maturity_date": self.maturity_date.isoformat(),
            "remaining_days": self.remaining_days,
            "credit_rating": self.credit_rating,
            "yield_to_maturity": self.yield_to_maturity,
            "price": self.price,
            "duration": self.duration,
            "convexity": self.convexity,
            "spread": self.spread,
            "accrued_interest": self.accrued_interest,
            # 数据来源标注：债券定价全部为模拟引擎生成
            "data_source": "SIMULATED",
        }


class YieldCurve:
    """收益率曲线"""
    
    def __init__(self):
        self.points: List[Dict] = []  # [(tenor_years, yield)]
        self.short_rate: float = 0.05
        self.long_rate: float = 0.06
        self.term_premium: float = 0.01
    
    def set_rates(self, short: float, long_: float, premium: float = 0.01):
        """设置收益率曲线"""
        self.short_rate = short
        self.long_rate = long_
        self.term_premium = premium
        self._rebuild_curve()
    
    def _rebuild_curve(self):
        """重建收益率曲线点"""
        self.points = []
        tenors = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]
        
        for t in tenors:
            if t <= 1:
                y = self.short_rate + (self.long_rate - self.short_rate) * t / 10
            else:
                y = self.long_rate + self.term_premium * math.log(t)
            self.points.append({"tenor": t, "yield": y})
    
    def get_yield(self, tenor: float) -> float:
        """获取指定期限的收益率"""
        if not self.points:
            return self.short_rate
        
        # 线性插值
        for i in range(len(self.points) - 1):
            if self.points[i]["tenor"] <= tenor <= self.points[i+1]["tenor"]:
                t1, y1 = self.points[i]["tenor"], self.points[i]["yield"]
                t2, y2 = self.points[i+1]["tenor"], self.points[i+1]["yield"]
                return y1 + (y2 - y1) * (tenor - t1) / (t2 - t1)
        
        # 超出范围
        if tenor < self.points[0]["tenor"]:
            return self.points[0]["yield"]
        return self.points[-1]["yield"]
    
    def shift(self, amount: float):
        """平行移动收益率曲线"""
        for point in self.points:
            point["yield"] += amount
        self.short_rate += amount
        self.long_rate += amount
    
    def get_tenors(self) -> List[Dict]:
        return self.points.copy()


class BondEngine:
    """债券引擎"""

    # 无风险利率缺省值：经济引擎不可用（离线/测试）时的保守假设
    DEFAULT_RISK_FREE_RATE = 0.05

    def __init__(self):
        self.bonds: Dict[str, Bond] = {}
        self.yield_curve = YieldCurve()
        self.yield_curve._rebuild_curve()  # 初始化收益率曲线
        self.history: List[Dict] = []
        # 当前无风险利率：由经济引擎 interest_rate 同步，spread 计算以此为基准
        self.risk_free_rate: float = self.DEFAULT_RISK_FREE_RATE

        # 初始化默认债券
        self._init_bonds()

    def sync_risk_free_rate(self) -> float:
        """从经济引擎同步无风险利率（interest_rate）。

        经济引擎未初始化或读取失败时保持当前值，绝不抛异常——
        债券引擎必须在任何环境下都可用。
        """
        try:
            from app.routers.economy import _economic_engine
            if _economic_engine is not None:
                rate = float(_economic_engine.state.interest_rate)
                if rate > 0:
                    self.risk_free_rate = rate
        except Exception as e:  # noqa: BLE001 - 同步失败保持原值
            logger.debug(f"sync_risk_free_rate failed, keeping {self.risk_free_rate}: {e}")
        return self.risk_free_rate
    
    # 当资产种子文件不可用时的兜底清单
    FALLBACK_BONDS = [
        # ticker, name, type, coupon, maturity_years, rating
        ("UST1Y", "US 1Y Treasury", "GOVERNMENT", 0.05, 1, "AAA"),
        ("UST5Y", "US 5Y Treasury", "GOVERNMENT", 0.055, 5, "AAA"),
        ("UST10Y", "US 10Y Treasury", "GOVERNMENT", 0.06, 10, "AAA"),
        ("UST30Y", "US 30Y Treasury", "GOVERNMENT", 0.065, 30, "AAA"),
        ("IG_AAA", "AAA Corporate Bond", "CORPORATE", 0.065, 10, "AAA"),
        ("IG_A", "A Corporate Bond", "CORPORATE", 0.075, 10, "A"),
        ("IG_BBB", "BBB Corporate Bond", "CORPORATE", 0.09, 10, "BBB"),
        ("HY_B", "B Corporate Bond", "CORPORATE", 0.11, 10, "B"),
        ("HY_HY", "HY Corporate Bond", "CORPORATE", 0.14, 10, "CCC"),
    ]

    @staticmethod
    def _load_seed_bonds():
        """从资产种子数据加载债券清单。

        覆盖各国国债收益率曲线与投资级/高收益公司债；种子文件缺失或不可解析时
        回退到内置的小清单，保证引擎始终可用。
        """
        seed = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "seed", "bonds.json",
        )
        if not os.path.exists(seed):
            logger.warning("bonds seed not found, falling back to builtin list")
            return None
        try:
            with open(seed, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read bonds seed ({e}), using builtin list")
            return None

    def _init_bonds(self):
        """初始化债券"""
        # 先同步无风险利率，使初始 spread 有真实基准
        self.sync_risk_free_rate()
        rows = self._load_seed_bonds()

        if rows:
            for r in rows:
                f = r.get("fundamentals") or {}
                ticker = r.get("ticker")
                if not ticker:
                    continue
                industry = r.get("industry") or ""
                btype = "GOVERNMENT" if "Government" in industry else "CORPORATE"
                years = float(f.get("maturity_years") or 10)
                # maturity_years 至少保留一个最短期限，避免 0 期限债券
                years = max(years, 0.25)
                try:
                    bond = Bond(
                        bond_id=ticker,
                        ticker=ticker,
                        name=r.get("name") or ticker,
                        bond_type=btype,
                        coupon_rate=float(f.get("coupon") or 0.05),
                        maturity_date=datetime.now() + timedelta(days=years * 365),
                        credit_rating=f.get("rating") or "AAA",
                    )
                    bond.update(float(f.get("yield") or 0.05), self.risk_free_rate)
                    self.bonds[ticker] = bond
                except Exception as e:
                    logger.warning(f"Skip seed bond {ticker}: {e}")
            if self.bonds:
                logger.info(f"BondEngine loaded {len(self.bonds)} bonds from seed")
                return

        # 兜底路径
        for ticker, name, btype, coupon, maturity, rating in self.FALLBACK_BONDS:
            bond = Bond(
                bond_id=ticker,
                ticker=ticker,
                name=name,
                bond_type=btype,
                coupon_rate=coupon,
                maturity_date=datetime.now() + timedelta(days=maturity * 365),
                credit_rating=rating,
            )
            bond.update(
                self.yield_curve.get_yield(maturity) + (0.01 if btype == "CORPORATE" else 0),
                self.risk_free_rate,
            )
            self.bonds[ticker] = bond
        logger.info(f"BondEngine initialized {len(self.bonds)} bonds from builtin list")

    def step(self, days: int = 1, shocks: Optional[Dict] = None):
        """推进债券市场"""
        import random

        # 每次推进前同步无风险利率，使 spread 跟随宏观利率演化
        self.sync_risk_free_rate()

        for day_index in range(days):
            # 收益率曲线移动
            rate_change = random.gauss(0, 0.0002)

            # 应用冲击
            if shocks:
                if "rate_hike" in shocks:
                    rate_change += shocks["rate_hike"] * 0.001
                if "rate_cut" in shocks:
                    rate_change -= shocks["rate_cut"] * 0.001

            self.yield_curve.shift(rate_change)

            # 更新所有债券
            for ticker, bond in self.bonds.items():
                base_yield = self.yield_curve.get_yield(bond.remaining_days / 365)
                spread = 0.01 if bond.bond_type == "CORPORATE" else 0

                # 信用利差变化
                if bond.bond_type == "CORPORATE" and shocks and "credit_spread_widen" in shocks:
                    spread += shocks["credit_spread_widen"] * 0.005

                bond.update(base_yield + spread, self.risk_free_rate)

            # 记录历史：每第 5 个模拟日记一次（按日内索引判断，
            # 旧代码用总天数 days % 5 判断，多日步进时要么每步都记要么从不记）
            if (day_index + 1) % 5 == 0:
                self.history.append({
                    "date": datetime.now().isoformat(),
                    "yield_curve": self.yield_curve.get_tenors(),
                    "bonds": {t: b.to_dict() for t, b in list(self.bonds.items())[:5]}
                })
    
    def get_bond(self, ticker: str) -> Optional[Bond]:
        return self.bonds.get(ticker)
    
    def get_all_bonds(self) -> List[Dict]:
        return [b.to_dict() for b in self.bonds.values()]
    
    def get_yield_curve(self) -> List[Dict]:
        return self.yield_curve.get_tenors()
    
    def apply_credit_event(self, ticker: str, rating_change: str):
        """应用信用事件"""
        bond = self.bonds.get(ticker)
        if bond:
            bond.credit_rating = rating_change
            # 更新利差
            spread_map = {"AAA": 0.005, "AA": 0.01, "A": 0.015, "BBB": 0.025, "BB": 0.05, "B": 0.08, "CCC": 0.12}
            base_yield = self.yield_curve.get_yield(bond.remaining_days / 365)
            spread = spread_map.get(rating_change, 0.1)
            bond.update(base_yield + spread, self.risk_free_rate)
            logger.info(f"Credit event: {ticker} rated {rating_change}")


if __name__ == "__main__":
    # 测试
    engine = BondEngine()
    
    print("Initial Yield Curve:")
    for point in engine.get_yield_curve():
        print(f"  {point['tenor']}Y: {point['yield']:.2%}")
    
    print("\nSample Bonds:")
    for ticker in ["UST10Y", "IG_AAA", "HY_B"]:
        bond = engine.get_bond(ticker)
        if bond:
            print(f"  {ticker}: price={bond.price:.2f}, ytm={bond.yield_to_maturity:.2%}, dur={bond.duration:.1f}Y")
    
    # 模拟收益率上升
    print("\nSimulating rate hike...")
    engine.step(10, {"rate_hike": 0.5})
    
    print("\nAfter rate hike:")
    for ticker in ["UST10Y", "IG_AAA", "HY_B"]:
        bond = engine.get_bond(ticker)
        if bond:
            print(f"  {ticker}: price={bond.price:.2f}, ytm={bond.yield_to_maturity:.2%}")
