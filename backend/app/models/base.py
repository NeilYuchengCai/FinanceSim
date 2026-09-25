"""
FinanceSim 基础模型
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 基础模型类"""
    pass


class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
