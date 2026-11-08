"""
FinanceSim 订单和交易模型
"""
from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class Order(Base):
    """
    订单表
    """
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True)  # UUID
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY, SELL
    type = Column(String(20), nullable=False)  # MARKET, LIMIT, STOP, STOP_LIMIT
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # 限价单价格
    stop_price = Column(Float, nullable=True)  # 止损价
    filled_quantity = Column(Float, default=0)
    avg_fill_price = Column(Float, default=0)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, PARTIAL, FILLED, CANCELLED
    created_by = Column(String(50), nullable=False, default="USER")  # USER, BOT_RETAIL, BOT_INSTITUTION, BOT_MARKET_MAKER
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    world = relationship("World", back_populates="orders")
    asset = relationship("Asset", back_populates="orders")
    buy_trades = relationship("Trade", back_populates="buy_order", foreign_keys="Trade.order_id_buy")
    sell_trades = relationship("Trade", back_populates="sell_order", foreign_keys="Trade.order_id_sell")
    
    def __repr__(self):
        return f"<Order(id={self.id}, side={self.side}, type={self.type}, status={self.status})>"


class Trade(Base):
    """
    成交表
    """
    __tablename__ = "trades"
    
    id = Column(String(36), primary_key=True)  # UUID
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    order_id_buy = Column(String(36), ForeignKey("orders.id"), nullable=True)
    order_id_sell = Column(String(36), ForeignKey("orders.id"), nullable=True)
    # 铁律②：核心金融金额/价格落地必须用 Decimal/Numeric，禁止 float 截断。
    price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    # 成交方向（相对发起方视角）：BUY / SELL。
    # nullable=True 兼容历史行；新成交由 trading_engine.submit_order 注入。
    direction = Column(String(10), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    world_day = Column(Integer, nullable=True, index=True)
    
    # 关系
    world = relationship("World", back_populates="trades")
    asset = relationship("Asset", back_populates="trades")
    buy_order = relationship("Order", back_populates="buy_trades", foreign_keys=[order_id_buy])
    sell_order = relationship("Order", back_populates="sell_trades", foreign_keys=[order_id_sell])
    
    def __repr__(self):
        return f"<Trade(price={self.price}, qty={self.quantity}, time={self.timestamp})>"


class Position(Base):
    """
    持仓表
    """
    __tablename__ = "positions"
    
    id = Column(String(36), primary_key=True)  # UUID
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    quantity = Column(Float, nullable=False, default=0)
    avg_price = Column(Float, nullable=False, default=0)
    last_price = Column(Float, nullable=False, default=0)
    unrealized_pnl = Column(Float, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    world = relationship("World", back_populates="positions")
    asset = relationship("Asset", back_populates="positions")
    
    # 唯一约束
    __table_args__ = ()
    
    def __repr__(self):
        return f"<Position(asset={self.asset_id}, qty={self.quantity})>"
