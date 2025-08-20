"""
Package models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime

from app.database import Base


class Package(Base):
    """Package model"""
    __tablename__ = "packages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    days = Column(Integer, nullable=False, default=1)
    cost_per_pax = Column(Numeric(10, 2), nullable=False, default=0.00)
    min_pax = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )