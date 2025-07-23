"""
Settings models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text

from app.database import Base


class GeneralSettings(Base):
    """General settings model for storing company information and bank details"""
    __tablename__ = "general_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(100), nullable=False)
    company_address = Column(Text, nullable=False)
    company_phone = Column(String(20), nullable=False)
    company_email = Column(String(100), nullable=False)
    
    # Bank account details
    bank_account_number = Column(String(50), nullable=False)
    bank_account_holder_name = Column(String(100), nullable=False)
    bank_name = Column(String(100), nullable=False)
    bank_swift_number = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)