"""
FinanceSim 事件和新闻模型
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class Event(Base):
    """
    事件表
    """
    __tablename__ = "events"
    
    id = Column(String(36), primary_key=True)  # UUID
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # COMPANY, EARNINGS, MA, MACRO, CENTRAL_BANK, etc.
    severity = Column(Float, nullable=True)
    title = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    affected_assets = Column(JSON, nullable=True)  # List of ticker
    affected_sectors = Column(JSON, nullable=True)  # List of sector names
    macro_effect = Column(JSON, nullable=True)  # 宏观影响
    sentiment_effect = Column(Float, nullable=True)  # 情绪影响
    propagation_depth = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    world = relationship("World", back_populates="events")
    news_items = relationship("News", back_populates="event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Event(type={self.type}, severity={self.severity})>"


class News(Base):
    """
    新闻表
    """
    __tablename__ = "news"
    
    id = Column(String(36), primary_key=True)  # UUID
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=True)
    headline = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    importance = Column(String(20), nullable=False, default="MARKET")  # BREAKING, MAJOR, IMPORTANT, MARKET, COMPANY, MACRO
    sentiment = Column(Float, nullable=True)  # -1.0 to 1.0
    affected_assets = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    world = relationship("World", back_populates="news")
    event = relationship("Event", back_populates="news_items")
    
    def __repr__(self):
        return f"<News(headline='{self.headline[:30]}...')>"


class MacroSnapshot(Base):
    """
    宏观经济快照表
    """
    __tablename__ = "macro_snapshots"
    
    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    day = Column(Integer, nullable=False, index=True)
    gdp_growth = Column(Float, nullable=True)
    inflation = Column(Float, nullable=True)
    unemployment = Column(Float, nullable=True)
    interest_rate = Column(Float, nullable=True)
    money_supply = Column(Float, nullable=True)
    consumer_confidence = Column(Float, nullable=True)
    industrial_production = Column(Float, nullable=True)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    world = relationship("World", backref="macro_snapshots")
    
    def __repr__(self):
        return f"<MacroSnapshot(world_id={self.world_id}, day={self.day})>"
