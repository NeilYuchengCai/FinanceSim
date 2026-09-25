"""
FinanceSim Trading Engine
负责交易规则管理
"""
import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from datetime import datetime

from app.engines.matching_engine import Order, OrderBook

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    交易引擎
    负责订单管理、撮合、成交
    """
    
    def __init__(self, world_id: int):
        self.world_id = world_id
        self.order_books: Dict[str, OrderBook] = {}  # ticker -> OrderBook
        self.pending_orders: Dict[str, Order] = {}   # order_id -> Order
        self.completed_orders: Dict[str, Order] = {}  # order_id -> Order
        self.trades: List[Dict] = []
    
    def get_or_create_orderbook(self, ticker: str) -> OrderBook:
        """获取或创建订单簿"""
        if ticker not in self.order_books:
            self.order_books[ticker] = OrderBook(ticker)
        return self.order_books[ticker]
    
    def submit_order(
        self,
        ticker: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        created_by: str = "USER"
    ) -> Dict:
        """
        提交订单
        
        Args:
            ticker: 标的代码
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP, STOP_LIMIT
            quantity: 数量
            price: 限价（可选）
            stop_price: 止损价（可选）
            created_by: 创建者
        """
        order_id = str(uuid.uuid4())
        quantity_dec = Decimal(str(quantity)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        price_dec = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if price else None
        stop_price_dec = Decimal(str(stop_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if stop_price else None
        
        order = Order(
            order_id=order_id,
            ticker=ticker,
            side=side,
            order_type=order_type,
            quantity=quantity_dec,
            price=price_dec,
            stop_price=stop_price_dec,
            created_by=created_by
        )
        
        # 获取订单簿并添加订单
        orderbook = self.get_or_create_orderbook(ticker)
        
        # 处理止损单
        if order_type in ("STOP", "STOP_LIMIT") and stop_price:
            # 检查是否触发
            current_price = self._get_current_price(ticker)
            if self._should_trigger_stop(order, current_price):
                # 转换为市价单或限价单
                order.type = "MARKET" if order_type == "STOP" else "LIMIT"
                order.price = order.stop_price
        
        # 添加到订单簿
        trades = orderbook.add_order(order)
        
        # 记录订单
        self.pending_orders[order_id] = order
        
        # 处理成交
        for trade in trades:
            trade["world_id"] = self.world_id
            trade["order_id_buy"] = trade.get("buyer_order_id")
            trade["order_id_sell"] = trade.get("seller_order_id")
            self.trades.append(trade)
            logger.info(f"Trade executed: {trade}")
        
        return {
            "order_id": order_id,
            "ticker": ticker,
            "side": side,
            "type": order_type,
            "quantity": float(quantity_dec),
            "price": float(price_dec) if price_dec else None,
            "status": order.status,
            "trades": trades
        }
    
    def cancel_order(self, order_id: str) -> Dict:
        """取消订单"""
        order = self.pending_orders.get(order_id)
        if not order:
            return {"success": False, "error": "Order not found"}
        
        orderbook = self.get_or_create_orderbook(order.ticker)
        success = orderbook.cancel_order(order_id)
        
        if success:
            order.status = "CANCELLED"
            del self.pending_orders[order_id]
            self.completed_orders[order_id] = order
        
        return {"success": success}
    
    def _should_trigger_stop(self, order: Order, current_price: float) -> bool:
        """检查止损单是否触发"""
        if order.side == "SELL":
            return current_price <= float(order.stop_price)
        else:  # BUY
            return current_price >= float(order.stop_price)
    
    def _get_current_price(self, ticker: str) -> float:
        """获取当前价格（从订单簿）"""
        orderbook = self.order_books.get(ticker)
        if not orderbook:
            return 100.0  # 默认价格
        
        spread = orderbook.get_spread()
        if spread:
            return float((spread[0] + spread[1]) / 2)
        
        return 100.0
    
    def get_orderbook(self, ticker: str, depth: int = 10) -> Dict:
        """获取订单簿"""
        orderbook = self.get_or_create_orderbook(ticker)
        return orderbook.get_depth(depth)
    
    def get_recent_trades(self, ticker: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """获取最近成交"""
        if ticker:
            return [t for t in self.trades if t.get("ticker") == ticker][-limit:]
        return self.trades[-limit:]
