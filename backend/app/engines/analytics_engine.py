"""
FinanceSim Analytics Engine
负责金融分析计算
"""
import math
import statistics
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class ReturnsResult:
    ticker: str
    returns: List[float]
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float


class AnalyticsEngine:
    """分析引擎"""
    
    @staticmethod
    def calculate_returns(prices: List[float]) -> List[float]:
        """计算收益率序列"""
        if len(prices) < 2:
            return []
        return [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    
    @staticmethod
    def annualized_return(returns: List[float], periods: int = 252) -> float:
        """年化收益率"""
        if not returns:
            return 0.0
        total_return = sum(returns)
        compound = 1.0
        for r in returns:
            compound *= (1 + r)
        years = periods / len(returns)
        if years <= 0:
            return 0.0
        return compound ** (1/years) - 1
    
    @staticmethod
    def volatility(returns: List[float], annualization: int = 252) -> float:
        """波动率"""
        if len(returns) < 2:
            return 0.0
        return statistics.stdev(returns) * math.sqrt(annualization)
    
    @staticmethod
    def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """夏普比率"""
        if len(returns) < 2:
            return 0.0
        excess_returns = [r - risk_free_rate/252 for r in returns]
        mean_excess = statistics.mean(excess_returns)
        std_excess = statistics.stdev(excess_returns)
        if std_excess == 0:
            return 0.0
        return mean_excess / std_excess * math.sqrt(252)
    
    @staticmethod
    def sortino_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """索提诺比率"""
        if len(returns) < 2:
            return 0.0
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return float('inf')
        
        excess_returns = [r - risk_free_rate/252 for r in returns]
        mean_excess = statistics.mean(excess_returns)
        downside_std = statistics.stdev(downside_returns) * math.sqrt(252)
        
        if downside_std == 0:
            return float('inf')
        return mean_excess / downside_std
    
    @staticmethod
    def max_drawdown(equity_curve: List[float]) -> Dict:
        """最大回撤"""
        if not equity_curve:
            return {"max_dd": 0.0, "start": 0, "end": 0, "peak": 0, "trough": 0}
        
        peak = equity_curve[0]
        max_dd = 0.0
        peak_idx = 0
        trough_idx = 0
        dd_start = 0
        dd_end = 0
        
        for i, value in enumerate(equity_curve):
            if value > peak:
                peak = value
                peak_idx = i
            dd = (peak - value) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                dd_start = peak_idx
                dd_end = i
                trough_idx = i
        
        return {
            "max_dd": max_dd,
            "start": dd_start,
            "end": dd_end,
            "peak": equity_curve[peak_idx],
            "trough": equity_curve[trough_idx],
            "recovery": dd_end - dd_start if dd_end > dd_start else 0
        }
    
    @staticmethod
    def var(returns: List[float], portfolio_value: float, confidence: float = 0.95) -> float:
        """Value at Risk (历史模拟法)"""
        if len(returns) < 10:
            return portfolio_value * 0.1  # 最小 VaR
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        var_percent = sorted_returns[max(0, index)]
        return abs(portfolio_value * var_percent)
    
    @staticmethod
    def cvar(returns: List[float], portfolio_value: float, confidence: float = 0.95) -> float:
        """Conditional VaR (Expected Shortfall)"""
        if len(returns) < 10:
            return portfolio_value * 0.15
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        tail_returns = sorted_returns[:max(1, index)]
        avg_tail = sum(tail_returns) / len(tail_returns)
        return abs(portfolio_value * avg_tail)
    
    @staticmethod
    def beta(returns_asset: List[float], returns_market: List[float]) -> float:
        """Beta 系数"""
        if len(returns_asset) != len(returns_market) or len(returns_asset) < 2:
            return 1.0
        
        cov = statistics.correlation(returns_asset, returns_market)
        var_market = statistics.variance(returns_market)
        
        if var_market == 0:
            return 1.0
        return cov * (statistics.stdev(returns_asset) / statistics.stdev(returns_market))
    
    @staticmethod
    def correlation(x: List[float], y: List[float]) -> float:
        """相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        return statistics.correlation(x, y)
    
    @staticmethod
    def correlation_matrix(prices_dict: Dict[str, List[float]], period: str = "daily") -> List[List[float]]:
        """相关矩阵"""
        tickers = list(prices_dict.keys())
        n = len(tickers)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i, t1 in enumerate(tickers):
            matrix[i][i] = 1.0
            for j, t2 in enumerate(tickers[i+1:], i+1):
                if len(prices_dict[t1]) != len(prices_dict[t2]):
                    continue
                returns1 = AnalyticsEngine.calculate_returns(prices_dict[t1])
                returns2 = AnalyticsEngine.calculate_returns(prices_dict[t2])
                if returns1 and returns2:
                    corr = AnalyticsEngine.correlation(returns1, returns2)
                    matrix[i][j] = corr
                    matrix[j][i] = corr
        
        return matrix
    
    @staticmethod
    def alpha(returns_asset: List[float], returns_market: List[float], 
              risk_free_rate: float = 0.02) -> float:
        """Alpha (詹森 Alpha)"""
        beta = AnalyticsEngine.beta(returns_asset, returns_market)
        market_return = sum(returns_market) / len(returns_market) * 252 if returns_market else 0
        asset_return = sum(returns_asset) / len(returns_asset) * 252 if returns_asset else 0
        
        expected_return = risk_free_rate + beta * (market_return - risk_free_rate)
        return asset_return - expected_return
    
    def analyze(self, ticker: str, prices: List[float], 
                market_prices: Optional[List[float]] = None) -> Dict:
        """综合分析"""
        returns = self.calculate_returns(prices)
        
        result = {
            "ticker": ticker,
            "periods": len(prices),
            "total_return": prices[-1]/prices[0] - 1 if prices else 0,
            "annualized_return": self.annualized_return(returns),
            "volatility": self.volatility(returns),
            "sharpe_ratio": self.sharpe_ratio(returns),
            "sortino_ratio": self.sortino_ratio(returns),
            "max_drawdown": self.max_drawdown(prices)
        }
        
        if market_prices and len(market_prices) == len(prices):
            market_returns = self.calculate_returns(market_prices)
            result.update({
                "beta": self.beta(returns, market_returns),
                "alpha": self.alpha(returns, market_returns)
            })
        
        return result
