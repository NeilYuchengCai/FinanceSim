"""
FinanceSim 商品资产模型
支持能源、贵金属、农产品、工业金属等商品类别
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Commodity(Base, TimestampMixin):
    """
    商品表
    存储大宗商品的基本信息
    """
    __tablename__ = "commodities"

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)  # 如 CL, GC, SI, ZC
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # ENERGY, METAL, AGRICULTURE, PRECIOUS_METAL
    subcategory = Column(String(100), nullable=True)  # 细分类别
    currency = Column(String(10), nullable=False, default="USD")
    exchange = Column(String(50), nullable=True)  # NYMEX, COMEX, CBOT等
    contract_size = Column(Float, nullable=True)  # 合约规模
    tick_size = Column(Float, nullable=True)  # 最小变动单位
    volatility = Column(Float, nullable=True)  # 年化波动率
    seasonality_factor = Column(Float, nullable=True, default=1.0)  # 季节性因子

    # 供需数据
    supply_demand = Column(JSON, nullable=True)  # {"supply": 1000, "demand": 950}
    inventory = Column(Float, nullable=True)  # 库存水平
    inventory_change = Column(Float, nullable=True)  # 库存变化

    # 基础价格（用于离线初始化）
    baseline_price = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)

    # 数据源标注
    data_source = Column(String(20), nullable=False, default="simulated")
    source_ts = Column(DateTime(timezone=True), nullable=True)

    # 关系
    world = relationship("World", back_populates="commodities")
    price_history = relationship("CommodityPriceHistory", back_populates="commodity", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('category IN (\'ENERGY\', \'METAL\', \'AGRICULTURE\', \'PRECIOUS_METAL\')',
                       name='chk_commodity_category'),
    )

    def __repr__(self):
        return f"<Commodity(ticker={self.ticker}, category={self.category})>"


class CommodityPriceHistory(Base):
    """
    商品价格历史表
    存储商品OHLCV数据
    """
    __tablename__ = "commodity_price_history"

    id = Column(Integer, primary_key=True, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, default=0)
    open_interest = Column(Integer, nullable=True)  # 未平仓合约

    # 供需快照
    supply_snapshot = Column(JSON, nullable=True)
    inventory_snapshot = Column(Float, nullable=True)

    # 关系
    commodity = relationship("Commodity", back_populates="price_history")

    __table_args__ = (
        # 唯一约束：同一商品同一时间戳只能有一条记录
        # 通过应用层保证
    )

    def __repr__(self):
        return f"<CommodityPriceHistory(commodity_id={self.commodity_id}, time={self.timestamp})>"
