"""
FinanceSim Trading Engine
负责交易规则管理（撮合 + 真实交易成本 + 合成盘口深度）

拟真改造要点：
1. 买卖价差（half-spread）：随资产年化波动率放大，波动率越高价差越宽（真实市场特征）。
2. 佣金：按成交额费率计收，设最低佣金下限。
3. 大单冲击（market impact）：通过**合成盘口深度**自然体现——市价单沿深度档位扫单，
   吃单越深、均价越差；小额订单仅在最优档成交（仅付价差），大额订单跨越多个档位（含冲击）。
4. 合成深度确定性生成（不引入随机），保证同一世界 + 同一状态可复现（确定性随机原则）。
5. 限价单：若穿越当前盘口（市价可成交）则按合成深度立即成交（受限于限价）；
   否则作为被动单留在真实 OrderBook，可在订单簿中查看、可撤单。
"""
import uuid
import logging
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from app.engines.matching_engine import Order, OrderBook

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- 真实交易成本参数
COMMISSION_RATE = 0.0005        # 成交额佣金费率（5 bps）
MIN_COMMISSION = Decimal("1.0")  # 最低佣金（计价货币单位）
BASE_HALF_SPREAD = 0.0002       # 基础半价差（2 bps），任何资产都有底线价差
SPREAD_VOL_COEFF = 0.0015       # 半价差对年化波动的敏感度
MIN_HALF_SPREAD = 0.0001        # 最小半价差（1 bp）
MAX_HALF_SPREAD = 0.01          # 最大半价差（1%，极端小盘）

# ---------------------------------------------------------------- 合成盘口深度参数
DEPTH_LEVELS = 15                # 合成盘口档位数
DEPTH_BASE_SHARE = 0.0005        # 每档基准量 = 该资产 ADV 的 0.05%
DEPTH_DECAY = 1.5                # 档位量随距离衰减指数（>1 => 远端更薄）
DEPTH_STEP_RATIO = 0.5           # 档位间距相对半价差的比例

# 各资产类别的日均成交额（美元）估算，用于把流动性量级映射到合成深度。
# 仅影响合成深度的"厚度"，不改变价格过程本身。
ADV_NOTIONAL = {
    "EQUITY": 5e8,
    "ETF": 2e9,
    "INDEX": 1e9,
    "FX": 1e11,
    "BOND": 1e9,
    "COMMODITY": 5e9,
}


class TradingEngine:
    """
    交易引擎
    负责订单管理、撮合、成交（含真实交易成本与合成盘口深度）
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

    # ------------------------------------------------------------ 行情/成本辅助
    def _get_asset_state(self, ticker: str) -> Tuple[float, float, float]:
        """返回 (中间价, 年化波动率, beta)；取不到时回退到合理默认。

        中间价来自实时行情流（唯一价格真相源）；年化波动率由 state.sigma 反推，
        beta 来自资产元数据。全部走内存，零额外 IO。
        """
        try:
            from app.services.market_stream import get_market_stream, SECONDS_PER_YEAR
            stream = get_market_stream()
            st = stream._assets.get(ticker) if stream is not None else None
            if st is not None:
                mid = float(st.price)
                annual_vol = float(st.sigma) * math.sqrt(SECONDS_PER_YEAR)
                beta = float(st.beta) if st.beta else 1.0
                return mid, annual_vol, beta
        except Exception:
            pass
        return 100.0, 0.25, 1.0

    def _half_spread(self, annual_vol: float) -> float:
        """半价差：基础价差 + 波动率敏感度，封顶在 [MIN, MAX]。"""
        hs = BASE_HALF_SPREAD + annual_vol * SPREAD_VOL_COEFF
        return max(MIN_HALF_SPREAD, min(MAX_HALF_SPREAD, hs))

    def _synth_depth(self, ticker: str, mid: float, annual_vol: float,
                     side: str) -> List[Tuple[float, float]]:
        """生成确定性合成盘口档位 (price, size)。

        - 最优档（i=0）即买/卖一档，含半价差；
        - 档位价格随距离按 step_pct 递增（卖）/ 递减（买）；
        - 档位量随距离按 (1+i)**DEPTH_DECAY 衰减（远端更薄）；
        - 基准量 = 该资产 ADV 的 DEPTH_BASE_SHARE，使不同流动性资产深度量级真实。
        完全确定性：仅依赖 (mid, vol, 资产类别)，不引入随机，保证可复现。
        """
        asset_class = self._asset_class_of(ticker)
        adv = ADV_NOTIONAL.get(asset_class, 5e8)
        base_size = max(1.0, (adv / mid) * DEPTH_BASE_SHARE) if mid > 0 else 1.0
        half = self._half_spread(annual_vol)
        step_pct = max(half * DEPTH_STEP_RATIO, 1e-5)
        levels: List[Tuple[float, float]] = []
        for i in range(DEPTH_LEVELS):
            if side == "BUY":
                # 买单扫的是卖盘（asks）：从 ask0 向上递增
                price = mid * (1.0 + half) * (1.0 + i * step_pct)
            else:
                price = mid * (1.0 - half) * (1.0 - i * step_pct)
            size = base_size / ((1.0 + i) ** DEPTH_DECAY)
            levels.append((price, size))
        return levels

    def _asset_class_of(self, ticker: str) -> str:
        try:
            from app.services.market_stream import get_market_stream
            st = get_market_stream()._assets.get(ticker)
            if st is not None:
                return (st.asset_type or "EQUITY").upper()
        except Exception:
            pass
        return "EQUITY"

    def _sweep(self, ticker: str, side: str, qty: float,
               limit: Optional[float] = None) -> Tuple[float, float, float]:
        """沿合成深度扫单，返回 (成交均价, 成交数量, 成交额)。

        - BUY 扫卖盘（asks）自最优档向上；SELL 扫买盘（bids）自最优档向下；
        - 若给出 limit，则仅成交价格不劣于限价的档位（BUY 不高于 limit，SELL 不低于 limit）；
        - 深度耗尽仍有未成交部分时，按最远档价格补齐（尾部流动性）。
        """
        mid, annual_vol, _beta = self._get_asset_state(ticker)
        levels = self._synth_depth(ticker, mid, annual_vol, side)
        remaining = float(qty)
        cost = 0.0
        filled = 0.0
        last_price = levels[-1][0]
        for price, size in levels:
            # 限价约束
            if limit is not None:
                if side == "BUY" and price > limit:
                    break
                if side == "SELL" and price < limit:
                    break
            take = min(remaining, size)
            if take <= 0:
                continue
            cost += take * price
            filled += take
            remaining -= take
            if remaining <= 1e-12:
                break
        if remaining > 1e-9:
            # 超出合成深度：以最远档价格补齐（极端大单的尾部冲击）
            cost += remaining * last_price
            filled += remaining
            remaining = 0.0
        avg = (cost / filled) if filled > 0 else mid
        notional = avg * filled
        return avg, filled, notional

    # ------------------------------------------------------------ 下单主流程
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

        # 处理止损单：触发条件满足时转换为市价/限价单
        if order_type in ("STOP", "STOP_LIMIT") and stop_price:
            current_price = self._get_current_price(ticker)
            if self._should_trigger_stop(order, current_price):
                order.type = "MARKET" if order_type == "STOP" else "LIMIT"
                order.price = order.stop_price

        trades: List[Dict] = []
        commission = Decimal("0")

        if order.type == "MARKET":
            trades, commission = self._fill_via_depth(order, None)
        elif order.type == "LIMIT":
            limit = float(order.price) if order.price else None
            # 是否穿越盘口（市价可成交）
            if self._is_marketable(ticker, side, limit):
                trades, commission = self._fill_via_depth(order, limit)
            else:
                # 被动单：留在真实 OrderBook，等待后续成交/可撤
                try:
                    trades = orderbook.add_order(order)
                except ValueError:
                    trades = []
                self.pending_orders[order_id] = order
        else:
            # 未知类型兜底：按市价处理
            trades, commission = self._fill_via_depth(order, None)

        for trade in trades:
            trade["world_id"] = self.world_id
            trade["order_id_buy"] = trade.get("buyer_order_id")
            trade["order_id_sell"] = trade.get("seller_order_id")
            trade.setdefault("direction", side)
            self.trades.append(trade)
            logger.info(f"Trade executed: {trade}")

        # 订单簿卫生：已完全成交的订单若残留在 bids/asks 中，按 id 摘除
        if order.remaining <= 0:
            orderbook.cancel_order(order_id)

        # 生命周期：成交/撤销的订单移出 pending
        if order.status in ("FILLED", "CANCELLED", "PARTIAL"):
            if order.remaining <= 0:
                self.pending_orders.pop(order_id, None)
                self.completed_orders[order_id] = order

        return {
            "order_id": order_id,
            "ticker": ticker,
            "side": side,
            "direction": side,
            "type": order_type,
            "quantity": float(quantity_dec),
            "price": float(price_dec) if price_dec else (float(order.price) if order.price else None),
            "stop_price": float(stop_price_dec) if stop_price_dec else None,
            "status": order.status,
            "filled_quantity": float(order.filled_quantity),
            "avg_fill_price": float(order.price) if order.filled_quantity > 0 and order.price else None,
            "commission": float(commission),
            "created_by": created_by,
            "trades": trades
        }

    def _fill_via_depth(self, order: Order, limit: Optional[float]
                        ) -> Tuple[List[Dict], Decimal]:
        """按合成深度成交一笔市价/可成交限价单，返回 (成交列表, 佣金)。"""
        qty = float(order.remaining)
        if qty <= 0:
            return [], Decimal("0")
        avg, filled, notional = self._sweep(order.ticker, order.side, qty, limit)
        if filled <= 0:
            return [], Decimal("0")

        fill_dec = Decimal(str(round(avg, 4)))
        qty_dec = Decimal(str(round(filled, 4)))
        order.filled_quantity = qty_dec
        order.price = fill_dec
        order.status = "FILLED"
        # 限价约束下若未完全成交，余量留在真实 OrderBook（被动）
        if limit is not None and abs(filled - qty) > 1e-9:
            order.status = "PARTIAL"
            remainder = Decimal(str(qty)) - qty_dec
            order.quantity = remainder  # 余量转为被动限价单等待

        # 佣金：费率计收，设最低下限
        notional_dec = Decimal(str(round(notional, 2)))
        commission = notional_dec * Decimal(str(COMMISSION_RATE))
        if commission < MIN_COMMISSION:
            commission = MIN_COMMISSION

        trade = {
            "id": str(uuid.uuid4()),
            "ticker": order.ticker,
            "price": float(fill_dec),
            "quantity": float(qty_dec),
            "buyer_order_id": order.id if order.side == "BUY" else None,
            "seller_order_id": order.id if order.side == "SELL" else None,
            "direction": order.side,
            "commission": float(commission),
            "timestamp": datetime.now(),
        }
        return [trade], commission

    def _is_marketable(self, ticker: str, side: str, limit: Optional[float]) -> bool:
        """判断限价单是否穿越当前盘口（可立即成交）。"""
        if limit is None:
            return True
        mid, annual_vol, _ = self._get_asset_state(ticker)
        half = self._half_spread(annual_vol)
        if side == "BUY":
            return limit >= mid * (1.0 + half)
        else:
            return limit <= mid * (1.0 - half)

    def cancel_order(self, order_id: str) -> Dict:
        order = self.pending_orders.get(order_id)
        if not order:
            return {"success": False, "error": "Order not found"}

        orderbook = self.get_or_create_orderbook(order.ticker)
        success = orderbook.cancel_order(order_id)

        if success or order.status in ("PARTIAL", "PENDING"):
            order.status = "CANCELLED"
            self.pending_orders.pop(order_id, None)
            self.completed_orders[order_id] = order
            return {"success": True}
        return {"success": False, "error": "Order not found"}

    def _should_trigger_stop(self, order: Order, current_price: float) -> bool:
        if order.side == "SELL":
            return current_price <= float(order.stop_price)
        else:
            return current_price >= float(order.stop_price)

    def _get_current_price(self, ticker: str) -> float:
        # 优先用行情流中间价；退化为订单簿价差中点；再退化为 100
        try:
            from app.services.market_stream import get_market_stream
            stream = get_market_stream()
            st = stream._assets.get(ticker) if stream is not None else None
            if st is not None and st.price > 0:
                return float(st.price)
        except Exception:
            pass
        orderbook = self.order_books.get(ticker)
        if orderbook:
            spread = orderbook.get_spread()
            if spread:
                return float((spread[0] + spread[1]) / 2)
        return 100.0

    def _get_market_price(self, ticker: str) -> Optional[float]:
        """从实时行情流取当前市场价，作为成交/预检参考。"""
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
