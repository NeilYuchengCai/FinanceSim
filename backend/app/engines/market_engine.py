"""
FinanceSim Market Engine
负责市场状态管理和价格更新
"""
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class MarketRegime:
    """
    市场状态机
    支持: CALM, BULL, BEAR, EUPHORIA, CORRECTION, PANIC, CRISIS, RECOVERY, RISK_ON, RISK_OFF
    """
    
    STATES = ["CALM", "BULL", "BEAR", "EUPHORIA", "CORRECTION", "PANIC", "CRISIS", "RECOVERY", "RISK_ON", "RISK_OFF"]
    
    def __init__(self):
        self.current_state = "CALM"
        self.momentum = 0.0
        self.volatility = 0.5
        self.sentiment = 0.5
        self.trend_persistence = 0.0
        
    def update(self, macro_data: Dict = None, events: List = None) -> str:
        """
        根据宏观数据和事件更新市场状态
        """
        # 计算综合指标
        momentum_score = self._calculate_momentum()
        vol_score = self._calculate_volatility()
        
        # 状态转换逻辑
        old_state = self.current_state
        
        if vol_score > 0.8 and momentum_score < -0.5:
            self.current_state = "CRISIS"
        elif vol_score > 0.6 and momentum_score < -0.3:
            self.current_state = "PANIC"
        elif vol_score > 0.5 and momentum_score > 0.3:
            self.current_state = "EUPHORIA"
        elif vol_score < 0.3 and momentum_score > 0.2:
            self.current_state = "BULL"
        elif vol_score < 0.3 and momentum_score < -0.2:
            self.current_state = "BEAR"
        elif vol_score > 0.4 and momentum_score < -0.1:
            self.current_state = "CORRECTION"
        elif vol_score < 0.2 and abs(momentum_score) < 0.1:
            self.current_state = "CALM"
        else:
            # 根据趋势持久性决定
            if self.trend_persistence > 0.5:
                self.current_state = "BULL" if momentum_score > 0 else "BEAR"
            else:
                self.current_state = "CALM"
        
        # 状态转换日志
        if self.current_state != old_state:
            logger.info(f"Market regime changed: {old_state} -> {self.current_state}")
        
        return self.current_state
    
    def _calculate_momentum(self) -> float:
        """计算动量指标"""
        # 简化实现：基于近期价格变化
        return self.momentum
    
    def _calculate_volatility(self) -> float:
        """计算波动率指标"""
        return self.volatility
    
    def get_volatility_multiplier(self) -> float:
        """获取波动率乘数"""
        multipliers = {
            "CALM": 0.8,
            "BULL": 1.0,
            "BEAR": 1.0,
            "EUPHORIA": 1.5,
            "CORRECTION": 1.3,
            "PANIC": 2.0,
            "CRISIS": 3.0,
            "RECOVERY": 1.2,
            "RISK_ON": 1.1,
            "RISK_OFF": 1.8
        }
        return multipliers.get(self.current_state, 1.0)
    
    def get_trend_bias(self) -> float:
        """获取趋势偏向"""
        biases = {
            "CALM": 0.0,
            "BULL": 0.0005,
            "BEAR": -0.0005,
            "EUPHORIA": 0.001,
            "CORRECTION": -0.0003,
            "PANIC": -0.001,
            "CRISIS": -0.002,
            "RECOVERY": 0.0003,
            "RISK_ON": 0.0005,
            "RISK_OFF": -0.0005
        }
        return biases.get(self.current_state, 0.0)


class MarketEngine:
    """
    市场引擎
    负责管理市场状态和价格更新
    """
    
    def __init__(self, world_id: int):
        self.world_id = world_id
        self.regime = MarketRegime()
        self.prices: Dict[str, Decimal] = {}  # ticker -> current price
        self.volumes: Dict[str, int] = {}     # ticker -> daily volume
        self.last_update: Optional[datetime] = None
        
    def update_price(self, ticker: str, old_price: Decimal, 
                     regime: MarketRegime, 
                     macro_sensitivity: float = 1.0,
                     event_impact: float = 0.0) -> Decimal:
        """
        更新单个资产价格
        使用几何布朗运动 + 事件影响
        """
        # 获取资产参数（需要从数据库查询）
        volatility = 0.25  # 默认年化波动率
        beta = 1.0
        
        # 日波动率
        daily_vol = volatility / (252 ** 0.5)
        
        # 波动率调整
        vol_multiplier = regime.get_volatility_multiplier()
        daily_vol *= vol_multiplier
        
        # 趋势偏向
        trend_bias = regime.get_trend_bias()
        
        # 随机项（几何布朗运动）
        drift = trend_bias + (beta * macro_sensitivity * 0.0001)
        diffusion = daily_vol * random.gauss(0, 1)
        
        # 事件影响
        jump = event_impact
        
        # 新价格
        new_price = old_price * (1 + drift + diffusion + jump)
        
        # 确保价格为正
        new_price = max(new_price, Decimal("0.01"))
        
        # 保留两位小数
        new_price = new_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        self.prices[ticker] = new_price
        
        # 更新成交量（随机）
        base_volume = 1_000_000
        vol_factor = regime.get_volatility_multiplier()
        self.volumes[ticker] = int(base_volume * vol_factor * random.uniform(0.5, 1.5))
        
        return new_price
    
    def batch_update(self, assets: List[Dict], 
                     regime: MarketRegime,
                     macro_data: Optional[Dict] = None,
                     events: Optional[List] = None) -> Dict[str, Decimal]:
        """
        批量更新所有资产价格
        """
        updates = {}
        
        for asset in assets:
            ticker = asset["ticker"]
            old_price = self.prices.get(ticker, Decimal(str(asset.get("price", 100))))
            
            # 计算宏观敏感度
            macro_sensitivity = asset.get("beta", 1.0) * macro_data.get("impact", 1.0) if macro_data else 1.0
            
            # 计算事件影响
            event_impact = 0.0
            if events:
                for event in events:
                    if ticker in event.get("affected_assets", []):
                        event_impact += event.get("severity", 0) * event.get("impact", 0.1)
            
            new_price = self.update_price(ticker, old_price, regime, macro_sensitivity, event_impact)
            updates[ticker] = new_price
        
        return updates
    
    def get_order_book(self, ticker: str, depth: int = 10) -> Dict:
        """
        生成订单簿（模拟）
        """
        current_price = self.prices.get(ticker, Decimal("100"))
        
        bids = []
        asks = []
        
        step = current_price * Decimal("0.001")  # 0.1% 步长
        
        for i in range(1, depth + 1):
            bid_price = current_price - step * i
            ask_price = current_price + step * i
            bids.append({"price": float(bid_price), "quantity": random.randint(100, 1000)})
            asks.append({"price": float(ask_price), "quantity": random.randint(100, 1000)})
        
        return {
            "ticker": ticker,
            "last_price": float(current_price),
            "bids": bids,
            "asks": asks
        }
