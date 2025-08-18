"""
Survey models for the XerpeX ERP System
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Survey(Base):
    """Survey model"""
    __tablename__ = "surveys"
    
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone_number = Column(String(20))
    estimated_paxes = Column(Integer, nullable=False)
    villa_types = Column(Text)
    notes = Column(Text)
    status = Column(String(20), default='new')
    priority = Column(String(10), default='medium')
    follow_up_date = Column(Date, nullable=True)
    visiting_date = Column(Date, nullable=True)
    salesmen_id = Column(Integer, ForeignKey("salesmen.id", ondelete="SET NULL"), default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salesman = relationship("Salesmen", back_populates="surveys")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'contacted', 'scheduled', 'visited', 'quoted', 'closed_won', 'closed_lost')",
            name='check_survey_status'
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name='check_survey_priority'
        ),
    )