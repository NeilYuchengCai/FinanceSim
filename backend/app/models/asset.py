"""
FinanceSim 资产模型
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Asset(Base, TimestampMixin):
    """
    资产表
    存储所有金融资产的基本信息
    """
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # EQUITY, ETF, INDEX, FX, BOND
    name = Column(String(255), nullable=True)
    exchange = Column(String(50), nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    market_cap = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)  # 当前价格
    fundamentals = Column(JSON, nullable=True)
    
    # 关系
    world = relationship("World", back_populates="assets")
    price_history = relationship("PriceHistory", back_populates="asset", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="asset", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="asset", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="asset", cascade="all, delete-orphan")
    
    # 唯一约束
    __table_args__ = (
        # world_id + ticker 唯一
        # 通过应用层保证，SQLite 不支持部分唯一索引
    )
    
    def __repr__(self):
        return f"<Asset(ticker={self.ticker}, type={self.type})>"


class PriceHistory(Base):
    """
    价格历史表
    存储每个资产的 OHLCV 数据
    """
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, default=0)
    data_source = Column(String(20), nullable=False, default="simulated")  # live, cached, historical, simulated, fallback
    source_ts = Column(DateTime(timezone=True), nullable=True)
    world_day = Column(Integer, nullable=True, index=True)
    
    # 关系
    asset = relationship("Asset", back_populates="price_history")
    
    def __repr__(self):
        return f"<PriceHistory(asset={self.asset_id}, time={self.timestamp})>"
