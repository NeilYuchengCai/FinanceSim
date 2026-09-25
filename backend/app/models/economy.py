"""
FinanceSim 用户经济模型
"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class UserEconomy(Base):
    """
    用户经济表
    存储用户的个人经济状况
    """
    __tablename__ = "user_economy"
    
    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), unique=True, nullable=False)
    cash = Column(Float, nullable=False, default=0)
    income_monthly = Column(Float, nullable=False, default=0)
    expenses_monthly = Column(Float, nullable=False, default=0)
    debt = Column(Float, nullable=False, default=0)
    credit_score = Column(Integer, nullable=False, default=700)
    tax_rate = Column(Float, nullable=False, default=0.2)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 约束
    __table_args__ = (
        CheckConstraint("cash >= 0", name="ck_cash_non_negative"),
        CheckConstraint("debt >= 0", name="ck_debt_non_negative"),
    )
    
    # 关系
    world = relationship("World", backref="user_economy")
    
    def net_worth(self, asset_prices: dict) -> float:
        """
        计算净值
        """
        # 需要从 Position 表获取持仓信息
        # 这里简化实现
        equity_value = sum(
            getattr(self, f"position_{asset}", 0) * price 
            for asset, price in asset_prices.items()
        )
        return self.cash + equity_value - self.debt
    
    def __repr__(self):
        return f"<UserEconomy(world_id={self.world_id}, cash={self.cash})>"
