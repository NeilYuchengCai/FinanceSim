"""
FinanceSim Economic Engine
负责宏观经济模拟
"""
import math
import logging
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _latest_float(observations) -> Optional[float]:
    """从 FRED 观测列表（按日期降序）取最新一条的浮点值；无有效值返回 None。"""
    if not observations:
        return None
    first = observations[0]
    raw = first.get("value") if isinstance(first, dict) else None
    if raw in (None, "", "."):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


@dataclass
class MacroState:
    """宏观经济状态"""
    gdp_growth: float = 0.025  # GDP增长率
    inflation: float = 0.02    # CPI通胀率
    unemployment: float = 0.05  # 失业率
    interest_rate: float = 0.05  # 基准利率
    money_supply: float = 1.0   # 货币供应量指数
    consumer_confidence: float = 1.0  # 消费者信心指数
    industrial_production: float = 1.0  # 工业生产指数
    trade_balance: float = 0.0   # 贸易收支
    
    # 经济周期
    cycle_position: float = 0.0  # -1 (衰退) 到 1 (扩张)
    cycle_phase: str = "EXPANSION"  # RECOVERY, EXPANSION, PEAK, CONTRACTION
    
    # 时间追踪
    simulated_date: datetime = field(default_factory=datetime.now)
    days_since_start: int = 0
    
    def update_cycle(self, gdp_trend: float, inflation_trend: float):
        """根据GDP和通胀趋势更新经济周期"""
        if gdp_trend < -0.01 and inflation_trend > 0.03:
            self.cycle_phase = "STAGNATION"
            self.cycle_position = -0.8
        elif gdp_trend < -0.005:
            self.cycle_phase = "RECESSION"
            self.cycle_position = -0.5
        elif gdp_trend > 0.015 and inflation_trend < 0.02:
            self.cycle_phase = "EXPANSION"
            self.cycle_position = 0.5
        elif gdp_trend > 0.02 and inflation_trend > 0.03:
            self.cycle_phase = "OVERHEAT"
            self.cycle_position = 0.8
        else:
            self.cycle_phase = "EXPANSION"
            self.cycle_position = 0.2
    
    def to_dict(self) -> Dict:
        return {
            "gdp_growth": self.gdp_growth,
            "inflation": self.inflation,
            "unemployment": self.unemployment,
            "interest_rate": self.interest_rate,
            "money_supply": self.money_supply,
            "consumer_confidence": self.consumer_confidence,
            "industrial_production": self.industrial_production,
            "trade_balance": self.trade_balance,
            "cycle_position": self.cycle_position,
            "cycle_phase": self.cycle_phase,
            "simulated_date": self.simulated_date.isoformat(),
            "days_since_start": self.days_since_start
        }


class EconomicEngine:
    """经济引擎 - 模拟宏观经济变量"""
    
    # 经济参数
    GDP_DAMPING = 0.15      # GDP变化阻尼
    INFLATION_DAMPING = 0.1  # 通胀变化阻尼
    UNEMPLOYMENT_DAMPING = 0.08  # 失业率变化阻尼
    RATE_RESPONSE = 0.3     # 利率对通胀/GDP的反应速度
    CONSUMER_CONFIDENCE_DRIFT = 0.02  # 消费者信心漂移
    
    # 经济周期参数
    CYCLE_PERIOD_DAYS = 252 * 4  # 约4年经济周期
    
    def __init__(self, initial_state: Optional[MacroState] = None):
        self.state = initial_state or MacroState()
        self.history: List[Dict] = []
        self._gdp_history: List[float] = []
        self._inflation_history: List[float] = []
        # 外部数据是否已用于种子/覆盖（保证只种子一次，不与合成演化反复打架）
        self._externally_seeded: bool = False

        # 记录初始状态
        self.history.append(self.state.to_dict())
    
    def step(self, days: int = 1, shocks: Optional[Dict] = None) -> MacroState:
        """
        推进经济模拟
        
        Args:
            days: 推进天数
            shocks: 外部冲击 {type: value}
        """
        for _ in range(days):
            self._step_daily(shocks or {})
            self.state.days_since_start += 1
            
            # 记录历史
            if self.state.days_since_start % 5 == 0:
                self.history.append(self.state.to_dict())
        
        return self.state
    
    def _step_daily(self, shocks: Dict):
        """单日经济更新"""
        # 计算GDP变化
        gdp_change = self._calc_gdp_change(shocks)
        old_gdp = self.state.gdp_growth
        self.state.gdp_growth += gdp_change * self.GDP_DAMPING
        self.state.gdp_growth = max(-0.10, min(0.15, self.state.gdp_growth))
        self._gdp_history.append(self.state.gdp_growth)
        
        # 计算通胀变化（菲利普斯曲线）
        inflation_change = self._calc_inflation_change(gdp_change, shocks)
        self.state.inflation += inflation_change * self.INFLATION_DAMPING
        self.state.inflation = max(-0.05, min(0.20, self.state.inflation))
        self._inflation_history.append(self.state.inflation)
        
        # 计算失业率变化（奥肯法则）
        unemployment_change = self._calc_unemployment_change(gdp_change)
        self.state.unemployment += unemployment_change
        self.state.unemployment = max(0.02, min(0.25, self.state.unemployment))
        
        # 更新利率（泰勒规则）
        self._update_interest_rate()
        
        # 更新消费者信心
        self._update_consumer_confidence(shocks)
        
        # 更新工业生产和货币供应
        self._update_industrial_production(gdp_change)
        self._update_money_supply(shocks)
        
        # 更新经济周期
        gdp_trend = self._calc_trend(self._gdp_history[-30:]) if len(self._gdp_history) >= 30 else 0
        inflation_trend = self._calc_trend(self._inflation_history[-30:]) if len(self._inflation_history) >= 30 else 0
        self.state.update_cycle(gdp_trend, inflation_trend)
        
        # 更新时间
        self.state.simulated_date += timedelta(days=1)
    
    def _calc_gdp_change(self, shocks: Dict) -> float:
        """计算GDP变化"""
        change = 0.0
        
        # 随机波动
        import random
        change += random.gauss(0, 0.003)
        
        # 均值回归到长期增长率
        long_term = 0.025
        change += (long_term - self.state.gdp_growth) * 0.01
        
        # 外部冲击
        if "gdp_shock" in shocks:
            change += shocks["gdp_shock"]
        if "recession_shock" in shocks:
            change -= shocks["recession_shock"] * 0.05
        if "stimulus_shock" in shocks:
            change += shocks["stimulus_shock"] * 0.03
        
        # 经济周期影响
        cycle_effect = self.state.cycle_position * 0.002
        change += cycle_effect
        
        return change
    
    def _calc_inflation_change(self, gdp_change: float, shocks: Dict) -> float:
        """计算通胀变化"""
        change = 0.0
        
        # 菲利普斯曲线：GDP增长推高通胀
        change += gdp_change * 0.5
        
        # 通胀预期
        expected_inflation = sum(self._inflation_history[-12:]) / min(12, len(self._inflation_history)) if self._inflation_history else 0.02
        change += (expected_inflation - self.state.inflation) * 0.1
        
        # 货币供应影响
        ms_growth = (self.state.money_supply - 1.0) / max(1, self.state.days_since_start)
        change += ms_growth * 0.2
        
        # 外部冲击
        if "inflation_shock" in shocks:
            change += shocks["inflation_shock"]
        if "supply_shock" in shocks:
            change += shocks["supply_shock"] * 0.02
        
        return change
    
    def _calc_unemployment_change(self, gdp_change: float) -> float:
        """计算失业率变化（奥肯法则）"""
        # GDP每超过2%，失业率下降0.5%
        gdp_excess = gdp_change - 0.02 / 252  # 日度潜在GDP增长
        return -gdp_excess * 0.5
    
    def _update_interest_rate(self):
        """更新利率（泰勒规则）"""
        inflation_gap = self.state.inflation - 0.02  # 目标通胀2%
        output_gap = self.state.gdp_growth - 0.025  # 潜在GDP增长
        
        target_rate = 0.02 + inflation_gap * 1.5 + output_gap * 0.5
        target_rate = max(0.0, min(0.20, target_rate))
        
        # 平滑调整
        self.state.interest_rate += (target_rate - self.state.interest_rate) * 0.1
    
    def _update_consumer_confidence(self, shocks: Dict):
        """更新消费者信心"""
        change = 0.0
        
        # 对GDP和就业的反应
        change += self.state.gdp_growth * 0.3
        change -= self.state.unemployment * 0.5
        change -= self.state.inflation * 0.2
        
        # 均值回归
        change += (1.0 - self.state.consumer_confidence) * 0.01
        
        # 随机波动
        import random
        change += random.gauss(0, 0.005)
        
        # 外部冲击
        if "confidence_shock" in shocks:
            change += shocks["confidence_shock"]
        
        self.state.consumer_confidence = max(0.3, min(1.7, self.state.consumer_confidence + change))
    
    def _update_industrial_production(self, gdp_change: float):
        """更新工业生产"""
        change = gdp_change * 1.2  # 工业生产波动更大
        import random
        change += random.gauss(0, 0.002)
        self.state.industrial_production *= (1 + change)
    
    def _update_money_supply(self, shocks: Dict):
        """更新货币供应"""
        change = 0.0001  # 日均增长0.01%
        
        # 央行干预
        if "monetary_policy" in shocks:
            change += shocks["monetary_policy"] * 0.001
        
        self.state.money_supply *= (1 + change)
    
    def _calc_trend(self, values: List[float]) -> float:
        """计算趋势"""
        if len(values) < 2:
            return 0.0
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        return numerator / denominator
    
    def get_macro_data(self) -> Dict:
        """获取当前宏观数据"""
        return self.state.to_dict()

    # ------------------------------------------------------------ 外部数据（可选）
    async def seed_from_external(self) -> bool:
        """可选：用 FRED 真实宏观序列覆盖/种子合成状态（只做一次）。

        仅当 FRED provider 启用且总开关打开时 ``maybe_fetch`` 才会返回数据；
        否则立即返回 ``False``，不影响任何合成行为。任何异常（网络/限额/解析）
        都被 ``maybe_fetch`` 吞掉并返回 ``None``，这里也安全返回 ``False``。

        返回 ``True`` 表示成功用真实数据覆盖了利率/失业/通胀。
        """
        if self._externally_seeded:
            return False
        from app.data.providers import get_provider, maybe_fetch

        fred = get_provider("fred")
        if fred is None or not fred.enabled:
            return False

        # CPI(通胀，需同比)、联邦基金利率、失业率
        series = await maybe_fetch(
            fred, series_ids=["CPIAUCSL", "FEDFUNDS", "UNRATE"], limit=13
        )
        if not series:
            return False

        self.apply_fred_series(series)
        self._externally_seeded = True
        logger.info("Macro state seeded from FRED external series")
        return True

    def apply_fred_series(self, series: Dict) -> None:
        """把 FRED 观测映射进宏状态（纯同步，便于测试直接调用）。

        FRED 数值是"百分比"量纲（如 5.33 表示 5.33%），本平台状态用小数（0.0533），
        因此利率/失业率需除以 100。通胀由 CPI 同比（YoY）近似。
        """
        # 利率：FEDFUNDS 最新值
        ff = _latest_float(series.get("FEDFUNDS"))
        if ff is not None:
            self.state.interest_rate = max(0.0, min(0.20, ff / 100.0))
        # 失业率：UNRATE 最新值
        un = _latest_float(series.get("UNRATE"))
        if un is not None:
            self.state.unemployment = max(0.02, min(0.25, un / 100.0))
        # 通胀：CPIAUCSL 同比（观测按日期降序，索引 0 最新、末尾约一年前）
        cpi = series.get("CPIAUCSL") or []
        if len(cpi) >= 2:
            try:
                now_v = float(cpi[0].get("value"))
                ya_v = float(cpi[-1].get("value"))
                if ya_v > 0:
                    yoy = now_v / ya_v - 1.0
                    self.state.inflation = max(-0.05, min(0.20, yoy))
            except (TypeError, ValueError):
                pass
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """获取历史数据"""
        return self.history[-limit:]
    
    def apply_shock(self, shock_type: str, magnitude: float = 1.0):
        """施加外部冲击"""
        shocks = {}
        
        shock_map = {
            "recession": ("recession_shock", magnitude),
            "stimulus": ("stimulus_shock", magnitude),
            "inflation_spike": ("inflation_shock", magnitude),
            "supply_shock": ("supply_shock", magnitude),
            "confidence_crisis": ("confidence_shock", -magnitude),
            "rate_hike": ("monetary_policy", -magnitude * 0.5),
        }
        
        if shock_type in shock_map:
            key, value = shock_map[shock_type]
            shocks[key] = value
        
        self.step(1, shocks)
        logger.info(f"Economic shock applied: {shock_type} = {magnitude}")


class CentralBank:
    """中央银行 - 货币政策决策"""
    
    def __init__(self, economic_engine: EconomicEngine):
        self.econ = economic_engine
        self.inflation_target = 0.02
        self.policy_rule = "taylor"  # taylor or simple
    
    def review_policy(self) -> Dict:
        """审查并调整货币政策"""
        state = self.econ.state
        
        if self.policy_rule == "taylor":
            inflation_gap = state.inflation - self.inflation_target
            output_gap = state.gdp_growth - 0.025
            
            target_rate = self.inflation_target + inflation_gap * 1.5 + output_gap * 0.5
            target_rate = max(0.0, min(0.15, target_rate))
            
            change = target_rate - state.interest_rate
        else:
            change = 0.0
        
        return {
            "current_rate": state.interest_rate,
            "target_rate": target_rate if self.policy_rule == "taylor" else state.interest_rate,
            "change": change,
            "inflation": state.inflation,
            "gdp_growth": state.gdp_growth,
            "unemployment": state.unemployment,
            "action": "ease" if change < -0.001 else "tighten" if change > 0.001 else "hold"
        }
    
    def implement_policy(self, action: str, magnitude: float = 0.25):
        """实施货币政策"""
        shocks = {}
        
        if action == "cut":
            shocks["monetary_policy"] = -magnitude / 100
        elif action == "hike":
            shocks["monetary_policy"] = magnitude / 100
        elif action == "qe":
            shocks["monetary_policy"] = -magnitude * 0.5 / 100
        
        self.econ.step(5, shocks)
        return self.review_policy()
