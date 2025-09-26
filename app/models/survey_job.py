"""
Survey Job models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class SurveyJob(Base):
    """Survey Job model for tracking email notifications"""
    __tablename__ = "survey_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default='pending', nullable=False)
    message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Relationships
    survey = relationship("Survey", back_populates="survey_jobs")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'success', 'failed')",
            name='check_survey_job_status'
        ),
    )