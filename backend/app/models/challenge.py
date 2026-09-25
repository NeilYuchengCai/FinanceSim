"""
FinanceSim Challenge Model
挑战模式 - 限定条件下完成特定目标的模拟挑战
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Challenge(Base):
    """
    挑战表
    每个挑战定义一个模拟目标和约束条件
    """
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_type = Column(String(50), nullable=False)  # beat_market, survive_crash, double_capital, etc.
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    target_days = Column(Integer, nullable=False)  # 挑战总天数
    constraints = Column(JSON, nullable=True)  # 限制条件（如不允许做空、最低现金比例等）
    initial_state = Column(JSON, nullable=True)  # 初始状态快照
    status = Column(String(20), nullable=False, default="active")  # active, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    world = relationship("World", back_populates="challenges")
    progress_logs = relationship("ChallengeProgress", back_populates="challenge", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Challenge(id={self.id}, type={self.challenge_type}, status={self.status})>"


class ChallengeProgress(Base):
    """
    挑战进度表
    记录挑战过程中的关键指标
    """
    __tablename__ = "challenge_progress"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(Integer, nullable=False)
    metrics = Column(JSON, nullable=True)  # 当日关键指标
    notes = Column(String(500), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    challenge = relationship("Challenge", back_populates="progress_logs")

    def __repr__(self):
        return f"<ChallengeProgress(challenge_id={self.challenge_id}, day={self.day})>"
