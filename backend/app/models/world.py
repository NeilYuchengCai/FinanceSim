"""
FinanceSim 世界模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class World(Base, TimestampMixin):
    """
    模拟世界表
    每个世界代表一个独立的模拟实例
    """
    __tablename__ = "worlds"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    mode = Column(String(50), nullable=False, default="simulation")  # sandbox, simulation, challenge, career
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    current_day = Column(Integer, default=0)
    seed = Column(String(64))
    is_archived = Column(Boolean, default=False)
    
    # 关系
    assets = relationship("Asset", back_populates="world", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="world", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="world", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="world", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="world", cascade="all, delete-orphan")
    news = relationship("News", back_populates="world", cascade="all, delete-orphan")
    macro_snapshots = relationship("MacroSnapshot", back_populates="world", cascade="all, delete-orphan")
    snapshots = relationship("WorldSnapshot", back_populates="world", cascade="all, delete-orphan")
    challenges = relationship("Challenge", back_populates="world", cascade="all, delete-orphan")
    commodities = relationship("Commodity", back_populates="world", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<World(id={self.id}, name='{self.name}', mode={self.mode})>"
