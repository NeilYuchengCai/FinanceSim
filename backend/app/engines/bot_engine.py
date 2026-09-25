"""
FinanceSim Bot Engine
负责模拟交易员（Bot）行为
"""
import random
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from app.engines.trading_engine import TradingEngine

logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """Bot 配置"""
    name: str
    strategy: str  # "momentum", "mean_reversion", "market_making", "random", "value", "growth", "macro", "pairs"
    risk_tolerance: float = 0.5  # 0-1
    capital: float = 100000.0
    max_position_size: float = 1000.0
    min_trade_size: float = 10.0
    
    # 策略参数
    momentum_window: int = 20
    mean_reversion_threshold: float = 0.02
    spread_capture: float = 0.0001
    pe_threshold: float = 20.0  # 价值投资PE阈值
    eps_growth_target: float = 0.15  # 成长投资EPS增长率目标
    macro_sensitivity: float = 0.5  # 宏观敏感度
    pair_correlation: float = 0.8  # 配对交易相关系数


@dataclass
class BotState:
    """Bot 状态"""
    config: BotConfig
    cash: float
    positions: Dict[str, float] = field(default_factory=dict)
    total_trades: int = 0
    total_pnl: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)


class BotEngine:
    """
    Bot 引擎
    管理多个自动化交易员
    """
    
    def __init__(self):
        self.bots: Dict[str, BotState] = {}
        self.trade_log: List[Dict] = []
    
    def add_bot(self, config: BotConfig) -> BotState:
        """添加一个新的 Bot"""
        bot = BotState(
            config=config,
            cash=config.capital
        )
        self.bots[config.name] = bot
        logger.info(f"Added bot: {config.name} with strategy: {config.strategy}")
        return bot
    
    def remove_bot(self, name: str) -> bool:
        """移除 Bot"""
        if name in self.bots:
            del self.bots[name]
            return True
        return False
    
    def step(self, trading_engine: TradingEngine, tickers: List[str], market_data: Dict) -> List[Dict]:
        """
        执行一步交易
        Returns: 本次交易的列表
        """
        all_trades = []
        
        for name, bot in self.bots.items():
            trades = self._execute_bot_trade(bot, trading_engine, tickers, market_data)
            all_trades.extend(trades)
        
        self.trade_log.extend(all_trades[-100:])  # 保留最近100条
        return all_trades
    
    def _execute_bot_trade(self, bot: BotState, trading_engine: TradingEngine, 
                          tickers: List[str], market_data: Dict) -> List[Dict]:
        """执行单个 Bot 的交易决策"""
        trades = []
        ticker = random.choice(tickers) if tickers else "AAPL"
        
        try:
            # 获取当前价格
            current_price = market_data.get(ticker, {}).get("price", 100.0)
            
            # 根据策略决定买卖
            decision = self._decide_action(bot, ticker, current_price, market_data)
            
            if decision["action"] == "BUY":
                trade = trading_engine.submit_order(
                    ticker=ticker,
                    side="BUY",
                    order_type="MARKET",
                    quantity=decision["quantity"],
                    price=current_price,
                    created_by=f"BOT:{bot.config.name}"
                )
                trades.append(trade)
                bot.cash -= decision["quantity"] * current_price
                bot.positions[ticker] = bot.positions.get(ticker, 0) + decision["quantity"]
                
            elif decision["action"] == "SELL":
                quantity = min(decision["quantity"], bot.positions.get(ticker, 0))
                if quantity > 0:
                    trade = trading_engine.submit_order(
                        ticker=ticker,
                        side="SELL",
                        order_type="MARKET",
                        quantity=quantity,
                        price=current_price,
                        created_by=f"BOT:{bot.config.name}"
                    )
                    trades.append(trade)
                    bot.cash += quantity * current_price
                    bot.positions[ticker] -= quantity
                    if bot.positions[ticker] <= 0:
                        del bot.positions[ticker]
            
            bot.total_trades += 1
            
        except Exception as e:
            logger.debug(f"Bot {bot.config.name} trade error: {e}")
        
        return trades
    
    def _decide_action(self, bot: BotState, ticker: str, price: float, 
                       market_data: Dict) -> Dict:
        """根据策略决定买卖"""
        strategy = bot.config.strategy
        risk = bot.config.risk_tolerance
        
        if strategy == "momentum":
            return self._momentum_strategy(bot, ticker, price, market_data)
        elif strategy == "mean_reversion":
            return self._mean_reversion_strategy(bot, ticker, price, market_data)
        elif strategy == "market_making":
            return self._market_making_strategy(bot, ticker, price, market_data)
        elif strategy == "value":
            return self._value_strategy(bot, ticker, price, market_data)
        elif strategy == "growth":
            return self._growth_strategy(bot, ticker, price, market_data)
        elif strategy == "macro":
            return self._macro_strategy(bot, ticker, price, market_data)
        elif strategy == "pairs":
            return self._pairs_strategy(bot, ticker, price, market_data)
        else:  # random
            return self._random_strategy(bot, ticker, price)
    
    def _momentum_strategy(self, bot: BotState, ticker: str, price: float, 
                          market_data: Dict) -> Dict:
        """动量策略"""
        history = market_data.get(ticker, {}).get("history", [])
        if len(history) < bot.config.momentum_window:
            return {"action": "HOLD", "quantity": 0}
        
        recent_prices = [h["price"] for h in history[-bot.config.momentum_window:]]
        trend = sum(1 for i in range(1, len(recent_prices)) if recent_prices[i] > recent_prices[i-1])
        trend_ratio = trend / len(recent_prices)
        
        if trend_ratio > 0.6 and bot.cash > 1000:
            quantity = min(bot.config.max_position_size, bot.cash / price * 0.1)
            return {"action": "BUY", "quantity": max(bot.config.min_trade_size, quantity)}
        elif trend_ratio < 0.4 and bot.positions.get(ticker, 0) > 0:
            quantity = min(100, bot.positions.get(ticker, 0))
            return {"action": "SELL", "quantity": max(bot.config.min_trade_size, quantity)}
        
        return {"action": "HOLD", "quantity": 0}
    
    def _mean_reversion_strategy(self, bot: BotState, ticker: str, price: float,
                                 market_data: Dict) -> Dict:
        """均值回归策略"""
        history = market_data.get(ticker, {}).get("history", [])
        if len(history) < 10:
            return {"action": "HOLD", "quantity": 0}
        
        recent_prices = [h["price"] for h in history[-20:]]
        avg_price = sum(recent_prices) / len(recent_prices)
        
        deviation = (price - avg_price) / avg_price
        
        if deviation < -bot.config.mean_reversion_threshold and bot.cash > 1000:
            quantity = min(bot.config.max_position_size, bot.cash / price * 0.1)
            return {"action": "BUY", "quantity": max(bot.config.min_trade_size, quantity)}
        elif deviation > bot.config.mean_reversion_threshold and bot.positions.get(ticker, 0) > 0:
            quantity = min(100, bot.positions.get(ticker, 0))
            return {"action": "SELL", "quantity": max(bot.config.min_trade_size, quantity)}
        
        return {"action": "HOLD", "quantity": 0}
    
    def _market_making_strategy(self, bot: BotState, ticker: str, price: float,
                                market_data: Dict) -> Dict:
        """做市策略"""
        trades = []
        
        # 卖出单
        if bot.cash > 1000:
            sell_price = price * (1 + bot.config.spread_capture)
            quantity = min(50, bot.cash / sell_price * 0.05)
            trades.append({
                "action": "SELL",
                "ticker": ticker,
                "quantity": max(bot.config.min_trade_size, quantity),
                "price": sell_price
            })
        
        # 买入单
        if bot.positions.get(ticker, 0) > 0:
            buy_price = price * (1 - bot.config.spread_capture)
            quantity = min(50, bot.positions.get(ticker, 0) * 0.1)
            trades.append({
                "action": "BUY",
                "ticker": ticker,
                "quantity": max(bot.config.min_trade_size, quantity),
                "price": buy_price
            })
        
        return trades[0] if trades else {"action": "HOLD", "quantity": 0}
    
    def _random_strategy(self, bot: BotState, ticker: str, price: float) -> Dict:
        """随机策略"""
        if random.random() < 0.3:  # 30% 概率交易
            action = "BUY" if random.random() > 0.5 else "SELL"
            quantity = random.uniform(bot.config.min_trade_size, bot.config.max_position_size)
            return {"action": action, "quantity": quantity}
        return {"action": "HOLD", "quantity": 0}
    
    def _value_strategy(self, bot: BotState, ticker: str, price: float,
                        market_data: Dict) -> Dict:
        """价值投资策略 - 低PE/高股息"""
        history = market_data.get(ticker, {}).get("history", [])
        fundamentals = market_data.get(ticker, {}).get("fundamentals", {})
        
        pe = fundamentals.get("pe_ratio", 25.0)
        dividend_yield = fundamentals.get("dividend_yield", 0.0)
        
        # 买入条件：PE低于阈值 或 股息率高
        if pe < bot.config.pe_threshold and bot.cash > 1000:
            quantity = min(bot.config.max_position_size, bot.cash / price * 0.08)
            return {"action": "BUY", "quantity": max(bot.config.min_trade_size, quantity)}
        # 卖出条件：PE过高
        elif pe > bot.config.pe_threshold * 1.5 and bot.positions.get(ticker, 0) > 0:
            quantity = min(100, bot.positions.get(ticker, 0))
            return {"action": "SELL", "quantity": max(bot.config.min_trade_size, quantity)}
        
        return {"action": "HOLD", "quantity": 0}
    
    def _growth_strategy(self, bot: BotState, ticker: str, price: float,
                         market_data: Dict) -> Dict:
        """成长投资策略 - EPS增长"""
        history = market_data.get(ticker, {}).get("history", [])
        fundamentals = market_data.get(ticker, {}).get("fundamentals", {})
        
        eps_growth = fundamentals.get("eps_growth", 0.1)
        
        # 买入条件：EPS增长超过目标
        if eps_growth > bot.config.eps_growth_target and bot.cash > 1000:
            quantity = min(bot.config.max_position_size, bot.cash / price * 0.08)
            return {"action": "BUY", "quantity": max(bot.config.min_trade_size, quantity)}
        # 卖出条件：增长放缓
        elif eps_growth < bot.config.eps_growth_target * 0.5 and bot.positions.get(ticker, 0) > 0:
            quantity = min(100, bot.positions.get(ticker, 0))
            return {"action": "SELL", "quantity": max(bot.config.min_trade_size, quantity)}
        
        return {"action": "HOLD", "quantity": 0}
    
    def _macro_strategy(self, bot: BotState, ticker: str, price: float,
                        market_data: Dict) -> Dict:
        """宏观策略 - 根据经济周期调整仓位"""
        macro_state = market_data.get("macro", {})
        gdp_growth = macro_state.get("gdp_growth", 0.025)
        inflation = macro_state.get("inflation", 0.02)
        interest_rate = macro_state.get("interest_rate", 0.05)
        
        # 经济景气时加仓，衰退时减仓
        economy_strength = gdp_growth - inflation
        
        if economy_strength > 0.02 and bot.cash > 2000:
            # 经济向好，增加仓位
            quantity = min(bot.config.max_position_size * 1.5, bot.cash / price * 0.15)
            return {"action": "BUY", "quantity": max(bot.config.min_trade_size, quantity)}
        elif economy_strength < -0.01 and bot.positions.get(ticker, 0) > 0:
            # 经济衰退，减仓
            quantity = min(150, bot.positions.get(ticker, 0) * 0.5)
            return {"action": "SELL", "quantity": max(bot.config.min_trade_size, quantity)}
        
        return {"action": "HOLD", "quantity": 0}
    
    def _pairs_strategy(self, bot: BotState, ticker: str, price: float,
                        market_data: Dict) -> Dict:
        """配对交易策略"""
        history = market_data.get(ticker, {}).get("history", [])
        
        if len(history) < 20:
            return {"action": "HOLD", "quantity": 0}
        
        # 计算短期和长期移动平均
        recent = [h["price"] for h in history[-10:]]
        longer = [h["price"] for h in history[-30:]]
        
        if len(longer) < 20:
            return {"action": "HOLD", "quantity": 0}
        
        short_ma = sum(recent) / len(recent)
        long_ma = sum(longer) / len(longer)
        
        # 价差
        spread = short_ma - long_ma
        spread_std = (sum((x - short_ma) ** 2 for x in recent) / len(recent)) ** 0.5
        
        if spread_std == 0:
            return {"action": "HOLD", "quantity": 0}
        
        z_score = spread / spread_std
        
        # 均值回归：价差过大时反向操作
        if z_score < -2 and bot.cash > 1000:
            quantity = min(bot.config.max_position_size, bot.cash / price * 0.05)
            return {"action": "BUY", "quantity": max(bot.config.min_trade_size, quantity)}
        elif z_score > 2 and bot.positions.get(ticker, 0) > 0:
            quantity = min(80, bot.positions.get(ticker, 0))
            return {"action": "SELL", "quantity": max(bot.config.min_trade_size, quantity)}
        
        return {"action": "HOLD", "quantity": 0}
    
    def get_stats(self) -> Dict:
        """获取所有 Bot 统计"""
        stats = []
        for name, bot in self.bots.items():
            stats.append({
                "name": name,
                "strategy": bot.config.strategy,
                "cash": bot.cash,
                "positions": bot.positions,
                "total_trades": bot.total_trades,
                "last_update": bot.last_update.isoformat()
            })
        return {"bots": stats, "total": len(stats)}
