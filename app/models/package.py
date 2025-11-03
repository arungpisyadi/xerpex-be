"""
Package models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Package(Base):
    """Package model"""
    __tablename__ = "packages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    days = Column(Integer, nullable=False, default=1)
    cost_per_pax = Column(Numeric(10, 2), nullable=False, default=0.00)
    min_pax = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="packages")
    quote_items = relationship("QuoteItem", back_populates="package")
    invoice_items = relationship("InvoiceItem", back_populates="package")
    booking_items = relationship("BookingItem", back_populates="package")
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )