"""
FinanceSim World Snapshot Model
快照表 - 保存世界某个时刻的完整状态
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class WorldSnapshot(Base):
    """
    世界快照表
    保存某个时刻的完整世界状态，支持回滚、分支、比较
    """
    __tablename__ = "world_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # 快照名称
    description = Column(Text, nullable=True)
    snapshot_day = Column(Integer, nullable=False)  # 快照时的世界天数
    snapshot_seed = Column(String(64), nullable=True)  # 快照时的seed
    summary_json = Column(JSON, nullable=True)  # 摘要信息（不存完整数据，仅元数据）
    full_state_json = Column(Text, nullable=True)  # 完整状态JSON（用于快照/恢复）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    world = relationship("World", back_populates="snapshots")

    def __repr__(self):
        return f"<WorldSnapshot(id={self.id}, world_id={self.world_id}, day={self.snapshot_day})>"
