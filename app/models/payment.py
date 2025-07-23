"""
Payment models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    """Payment model"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False)
    notes = Column(Text)
    recorded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Relationships
    booking = relationship("Booking", back_populates="payments")
    recorded_by_user = relationship("User", back_populates="recorded_payments")


class Invoice(Base):
    """Invoice model"""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = relationship("Booking", back_populates="invoices")