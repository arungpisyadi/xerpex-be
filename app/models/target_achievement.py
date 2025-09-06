"""
Target Achievement models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.database import Base


class TargetAchievement(Base):
    """Target Achievement model"""
    __tablename__ = "target_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    achieved_amount = Column(Numeric(precision=15, scale=2), nullable=False, default=0)
    target_amount = Column(Numeric(precision=15, scale=2), nullable=False)
    achievement_percentage = Column(Numeric(precision=5, scale=2), nullable=False, default=0)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="target_achievements")