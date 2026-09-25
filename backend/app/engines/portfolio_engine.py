"""
FinanceSim Portfolio Engine
负责持仓和资金管理
"""
import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Position:
    """持仓类"""
    
    def __init__(self, ticker: str, quantity: Decimal = Decimal("0"), avg_price: Decimal = Decimal("0")):
        self.ticker = ticker
        self.quantity = quantity
        self.avg_price = avg_price
        self.last_price = Decimal("0")
        self.realized_pnl = Decimal("0")
        self.unrealized_pnl = Decimal("0")
    
    @property
    def market_value(self) -> Decimal:
        return self.quantity * self.last_price
    
    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.avg_price
    
    @property
    def pnl_percent(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return float((self.market_value - self.cost_basis) / self.cost_basis * 100)
    
    def update_price(self, price: Decimal):
        self.last_price = price
        self.unrealized_pnl = self.market_value - self.cost_basis
    
    def close(self) -> Decimal:
        """平仓，返回已实现收益"""
        realized = self.realized_pnl
        self.quantity = Decimal("0")
        self.realized_pnl = Decimal("0")
        self.unrealized_pnl = Decimal("0")
        return realized


class PortfolioEngine:
    """投资组合引擎"""
    
    def __init__(self, world_id: int, initial_cash: Decimal = Decimal("100000")):
        self.world_id = world_id
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        self.equity_curve: List[Dict] = []
    
    def buy(self, ticker: str, quantity: float, price: float, trade_id: str = None) -> Dict:
        """买入"""
        quantity_dec = Decimal(str(quantity)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        price_dec = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cost = quantity_dec * price_dec
        
        if cost > self.cash:
            raise ValueError(f"Insufficient funds: need {cost}, have {self.cash}")
        
        # 更新现金
        self.cash -= cost
        
        # 更新持仓
        if ticker not in self.positions:
            self.positions[ticker] = Position(ticker, Decimal("0"), Decimal("0"))
        
        pos = self.positions[ticker]
        old_cost = pos.avg_price * pos.quantity
        pos.quantity += quantity_dec
        pos.avg_price = (old_cost + cost) / pos.quantity
        pos.update_price(price_dec)
        
        # 记录交易
        trade = {
            "type": "BUY",
            "ticker": ticker,
            "quantity": float(quantity_dec),
            "price": float(price_dec),
            "cost": float(cost),
            "timestamp": datetime.now(),
            "trade_id": trade_id
        }
        self.trade_history.append(trade)
        
        logger.info(f"Bought {quantity} {ticker} @ {price}")
        
        return trade
    
    def sell(self, ticker: str, quantity: float, price: float, trade_id: str = None) -> Dict:
        """卖出"""
        if ticker not in self.positions:
            raise ValueError(f"No position in {ticker}")
        
        pos = self.positions[ticker]
        quantity_dec = Decimal(str(quantity)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        price_dec = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        if quantity_dec > pos.quantity:
            raise ValueError(f"Insufficient position: have {pos.quantity}, need {quantity_dec}")
        
        # 计算已实现收益
        realized_pnl = (price_dec - pos.avg_price) * quantity_dec
        pos.realized_pnl += realized_pnl
        
        # 更新现金
        self.cash += quantity_dec * price_dec
        
        # 更新持仓
        pos.quantity -= quantity_dec
        pos.update_price(price_dec)
        
        # 清除空持仓
        if pos.quantity == 0:
            del self.positions[ticker]
        
        # 记录交易
        trade = {
            "type": "SELL",
            "ticker": ticker,
            "quantity": float(quantity_dec),
            "price": float(price_dec),
            "proceeds": float(quantity_dec * price_dec),
            "realized_pnl": float(realized_pnl),
            "timestamp": datetime.now(),
            "trade_id": trade_id
        }
        self.trade_history.append(trade)
        
        logger.info(f"Sold {quantity} {ticker} @ {price}, PnL={realized_pnl}")
        
        return trade
    
    def update_prices(self, prices: Dict[str, float]):
        """批量更新价格"""
        for ticker, price in prices.items():
            if ticker in self.positions:
                price_dec = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                self.positions[ticker].update_price(price_dec)
    
    def get_position(self, ticker: str) -> Optional[Dict]:
        """获取持仓详情"""
        pos = self.positions.get(ticker)
        if not pos:
            return None
        return {
            "ticker": pos.ticker,
            "quantity": float(pos.quantity),
            "avg_price": float(pos.avg_price),
            "last_price": float(pos.last_price),
            "market_value": float(pos.market_value),
            "cost_basis": float(pos.cost_basis),
            "unrealized_pnl": float(pos.unrealized_pnl),
            "realized_pnl": float(pos.realized_pnl),
            "pnl_percent": pos.pnl_percent
        }
    
    def get_all_positions(self) -> List[Dict]:
        """获取所有持仓"""
        return [self.get_position(t) for t in self.positions.keys()]
    
    def net_worth(self, prices: Dict[str, float] = None) -> float:
        """计算净值"""
        equity_value = Decimal("0")
        for ticker, pos in self.positions.items():
            price = Decimal(str(prices.get(ticker, pos.last_price)))
            pos.update_price(price)
            equity_value += pos.market_value
        
        return float(self.cash + equity_value)
    
    def get_performance(self) -> Dict:
        """获取绩效指标"""
        total_value = self.net_worth()
        total_invested = sum(t["cost"] for t in self.trade_history if t["type"] == "BUY")
        total_realized = sum(t.get("realized_pnl", 0) for t in self.trade_history if t["type"] == "SELL")
        
        return {
            "cash": float(self.cash),
            "total_value": total_value,
            "total_invested": total_invested,
            "total_realized_pnl": total_realized,
            "unrealized_pnl": float(sum(p.unrealized_pnl for p in self.positions.values())),
            "net_worth": total_value
        }
