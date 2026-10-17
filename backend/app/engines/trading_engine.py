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
        self.order_books: Dict[str, OrderBook] = {}
        self.pending_orders: Dict[str, Order] = {}
        self.completed_orders: Dict[str, Order] = {}
        self.trades: List[Dict] = []
    
    def get_or_create_orderbook(self, ticker: str) -> OrderBook:
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
        
        orderbook = self.get_or_create_orderbook(ticker)

        # 处理止损单
        if order_type in ("STOP", "STOP_LIMIT") and stop_price:
            current_price = self._get_current_price(ticker)
            if self._should_trigger_stop(order, current_price):
                order.type = "MARKET" if order_type == "STOP" else "LIMIT"
                order.price = order.stop_price

        try:
            trades = orderbook.add_order(order)
        except ValueError:
            # 没有对手盘（例如孤立的市价单）：先当作无成交，下面用流动性兜底处理
            trades = []
        self.pending_orders[order_id] = order

        # 流动性兜底：市价单若没有对手盘，按当前市场价直接成交，
        # 保证用户与 AI 交易员都能随时成交（模拟环境无需挂单等待）。
        if order_type == "MARKET" and order.remaining > 0:
            mid = self._get_market_price(ticker)
            if mid and mid > 0:
                qty = order.remaining
                fill = Decimal(str(round(float(mid), 2)))
                if order.side == "BUY":
                    fill = (fill * Decimal("1.0005")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                else:
                    fill = (fill * Decimal("0.9995")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                synth = {
                    "id": str(uuid.uuid4()),
                    "ticker": ticker,
                    "price": float(fill),
                    "quantity": float(qty),
                    "buyer_order_id": order.id if order.side == "BUY" else None,
                    "seller_order_id": order.id if order.side == "SELL" else None,
                    "timestamp": datetime.now(),
                }
                order.filled_quantity = order.original_quantity
                order.price = fill
                order.status = "FILLED"
                trades.append(synth)

        for trade in trades:
            trade["world_id"] = self.world_id
            trade["order_id_buy"] = trade.get("buyer_order_id")
            trade["order_id_sell"] = trade.get("seller_order_id")
            self.trades.append(trade)
            logger.info(f"Trade executed: {trade}")

        # 订单簿卫生：已完全成交的订单若残留在 bids/asks 中，
        # get_depth 会统计出 quantity=0 的幽灵档位，这里按 id 摘除。
        if order.remaining <= 0:
            orderbook.cancel_order(order_id)

        # 生命周期：成交/撤销的订单移出 pending，避免"已成交订单"仍挂在订单列表
        if order.status in ("FILLED", "CANCELLED"):
            self.pending_orders.pop(order_id, None)
            self.completed_orders[order_id] = order

        return {
            "order_id": order_id,
            "ticker": ticker,
            "side": side,
            "type": order_type,
            "quantity": float(quantity_dec),
            "price": float(price_dec) if price_dec else (float(order.price) if order.price else None),
            "stop_price": float(stop_price_dec) if stop_price_dec else None,
            "status": order.status,
            "filled_quantity": float(order.filled_quantity),
            "avg_fill_price": float(order.price) if order.filled_quantity > 0 and order.price else None,
            "created_by": created_by,
            "trades": trades
        }
    
    def cancel_order(self, order_id: str) -> Dict:
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
        if order.side == "SELL":
            return current_price <= float(order.stop_price)
        else:
            return current_price >= float(order.stop_price)
    
    def _get_current_price(self, ticker: str) -> float:
        orderbook = self.order_books.get(ticker)
        if not orderbook:
            return 100.0
        spread = orderbook.get_spread()
        if spread:
            return float((spread[0] + spread[1]) / 2)
        return 100.0

    def _get_market_price(self, ticker: str) -> Optional[float]:
        """从实时行情流取当前市场价，作为市价单兜底成交价。"""
        try:
            from app.services.market_stream import get_market_stream
            stream = get_market_stream()
            state = stream._assets.get(ticker)
            if state is not None:
                return float(state.price)
        except Exception:
            pass
        return None
    
    def get_orderbook(self, ticker: str, depth: int = 10) -> Dict:
        orderbook = self.get_or_create_orderbook(ticker)
        return orderbook.get_depth(depth)
    
    def get_recent_trades(self, ticker: Optional[str] = None, limit: int = 100) -> List[Dict]:
        if ticker:
            return [t for t in self.trades if t.get("ticker") == ticker][-limit:]
        return self.trades[-limit:]
