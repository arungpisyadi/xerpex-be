"""
Sales Target models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.database import Base


class Target(Base):
    """Sales Target model"""
    __tablename__ = "sales_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    target_amount = Column(Numeric(precision=15, scale=2), nullable=False)
    carried_over_amount = Column(Numeric(precision=15, scale=2), nullable=False, default=0)
    adjusted_target_amount = Column(Numeric(precision=15, scale=2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="targets")