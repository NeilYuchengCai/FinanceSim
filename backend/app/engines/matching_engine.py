"""
FinanceSim Matching Engine
负责订单撮合
"""
import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class Order:
    """订单类"""
    
    def __init__(
        self,
        order_id: str,
        ticker: str,
        side: str,  # BUY or SELL
        order_type: str,  # MARKET, LIMIT, STOP, STOP_LIMIT
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        created_by: str = "USER"
    ):
        self.id = order_id
        self.ticker = ticker
        self.side = side
        self.type = order_type
        self.quantity = quantity
        self.original_quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.filled_quantity = Decimal("0")
        self.status = "PENDING"  # PENDING, PARTIAL, FILLED, CANCELLED
        self.created_by = created_by
        self.created_at = datetime.now()
    
    @property
    def remaining(self) -> Decimal:
        return self.original_quantity - self.filled_quantity
    
    @property
    def avg_fill_price(self) -> Optional[Decimal]:
        if self.filled_quantity == 0:
            return None
        return self.price if self.price else None
    
    def is_filled(self) -> bool:
        return self.filled_quantity >= self.original_quantity
    
    def __repr__(self):
        return f"<Order({self.id}, {self.side} {self.type} {self.ticker} qty={self.remaining})>"


class OrderBook:
    """订单簿"""
    
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.bids: Dict[Decimal, List[Order]] = {}  # price -> [orders]
        self.asks: Dict[Decimal, List[Order]] = {}
        self.trades: List[Dict] = []
    
    def add_order(self, order: Order) -> List[Dict]:
        """添加订单并尝试撮合"""
        trades = []
        
        if order.side == "BUY":
            self._add_bid(order)
        else:
            self._add_ask(order)
        
        # 尝试撮合
        trades = self._match()
        
        return trades
    
    def _add_bid(self, order: Order):
        """添加买单"""
        price = order.price
        if price is None:
            # 市价单，使用当前最优卖价
            price = self._best_ask()
            if price is None:
                raise ValueError(f"No ask orders for {self.ticker}")
        
        if price not in self.bids:
            self.bids[price] = []
        self.bids[price].append(order)
    
    def _add_ask(self, order: Order):
        """添加卖单"""
        price = order.price
        if price is None:
            # 市价单，使用当前最优买价
            price = self._best_bid()
            if price is None:
                raise ValueError(f"No bid orders for {self.ticker}")
        
        if price not in self.asks:
            self.asks[price] = []
        self.asks[price].append(order)
    
    def _best_bid(self) -> Optional[Decimal]:
        """获取最优买价"""
        if not self.bids:
            return None
        return max(self.bids.keys())
    
    def _best_ask(self) -> Optional[Decimal]:
        """获取最优卖价"""
        if not self.asks:
            return None
        return min(self.asks.keys())
    
    def _match(self) -> List[Dict]:
        """撮合逻辑"""
        trades = []
        
        while True:
            best_bid = self._best_bid()
            best_ask = self._best_ask()
            
            if best_bid is None or best_ask is None:
                break
            
            if best_bid < best_ask:
                break  # 没有交叉
            
            # 撮合
            trade = self._execute_trade(best_bid, best_ask)
            trades.append(trade)
            
            # 清理已完成的订单
            self._cleanup()
        
        return trades
    
    def _execute_trade(self, bid_price: Decimal, ask_price: Decimal) -> Dict:
        """执行成交"""
        bid_orders = self.bids[bid_price]
        ask_orders = self.asks[ask_price]
        
        if not bid_orders or not ask_orders:
            return None
        
        buyer = bid_orders[0]
        seller = ask_orders[0]
        
        # 成交数量
        trade_qty = min(buyer.remaining, seller.remaining)
        
        # 成交价格（取中间价）
        trade_price = (bid_price + ask_price) / 2
        trade_price = trade_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # 更新订单
        buyer.filled_quantity += trade_qty
        seller.filled_quantity += trade_qty
        buyer.price = trade_price
        seller.price = trade_price
        
        # 检查是否完成
        if buyer.is_filled():
            buyer.status = "FILLED"
            self.bids[bid_price].pop(0)
            if not self.bids[bid_price]:
                del self.bids[bid_price]
        
        if seller.is_filled():
            seller.status = "FILLED"
            self.asks[ask_price].pop(0)
            if not self.asks[ask_price]:
                del self.asks[ask_price]
        
        # 生成成交记录
        trade = {
            "id": str(uuid.uuid4()),
            "ticker": self.ticker,
            "price": float(trade_price),
            "quantity": float(trade_qty),
            "buyer_order_id": buyer.id,
            "seller_order_id": seller.id,
            "timestamp": datetime.now()
        }
        
        self.trades.append(trade)
        logger.info(f"Trade executed: {self.ticker} @ {trade_price} qty={trade_qty}")
        
        return trade
    
    def _cleanup(self):
        """清理已完成的订单"""
        self.bids = {p: o for p, o in self.bids.items() if any(not order.is_filled() for order in o)}
        self.asks = {p: o for p, o in self.asks.items() if any(not order.is_filled() for order in o)}
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        # 检查买单
        for price, orders in self.bids.items():
            for i, order in enumerate(orders):
                if order.id == order_id:
                    orders.pop(i)
                    if not orders:
                        del self.bids[price]
                    return True
        
        # 检查卖单
        for price, orders in self.asks.items():
            for i, order in enumerate(orders):
                if order.id == order_id:
                    orders.pop(i)
                    if not orders:
                        del self.asks[price]
                    return True
        
        return False
    
    def get_spread(self) -> Optional[Tuple[Decimal, Decimal]]:
        """获取买卖价差"""
        best_bid = self._best_bid()
        best_ask = self._best_ask()
        
        if best_bid is None or best_ask is None:
            return None
        
        return (best_bid, best_ask)
    
    def get_depth(self, levels: int = 5) -> Dict:
        """获取订单簿深度"""
        sorted_bids = sorted(self.bids.items(), reverse=True)[:levels]
        sorted_asks = sorted(self.asks.items())[:levels]
        
        return {
            "bids": [{"price": float(p), "quantity": sum(o.remaining for o in orders)} for p, orders in sorted_bids],
            "asks": [{"price": float(p), "quantity": sum(o.remaining for o in orders)} for p, orders in sorted_asks]
        }


class MatchingEngine:
    """订单撮合引擎"""
    
    def __init__(self):
        self.order_books: Dict[str, OrderBook] = {}
    
    def get_or_create_book(self, ticker: str) -> OrderBook:
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
        """提交订单"""
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
        
        book = self.get_or_create_book(ticker)
        trades = book.add_order(order)
        
        return {
            "order_id": order_id,
            "ticker": ticker,
            "side": side,
            "type": order_type,
            "quantity": float(quantity_dec),
            "price": float(price_dec) if price_dec else None,
            "status": order.status,
            "filled_quantity": float(order.filled_quantity),
            "remaining_quantity": float(order.remaining),
            "trades": trades
        }
    
    def cancel_order(self, ticker: str, order_id: str) -> Dict:
        """取消订单"""
        book = self.order_books.get(ticker)
        if not book:
            return {"success": False, "error": "Order book not found"}
        
        success = book.cancel_order(order_id)
        return {"success": success}
    
    def get_orderbook(self, ticker: str, depth: int = 10) -> Dict:
        """获取订单簿"""
        book = self.order_books.get(ticker)
        if not book:
            return {"ticker": ticker, "bids": [], "asks": [], "spread": None}
        return book.get_depth(depth)
