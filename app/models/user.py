"""
User models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("Booking", foreign_keys="Booking.user_id", back_populates="user", cascade="all, delete-orphan")
    sales_person_bookings = relationship("Booking", foreign_keys="Booking.sales_person_id", back_populates="sales_person")
    updated_availabilities = relationship("VillaAvailability", back_populates="updated_by_user")
    
    # Invoicing system relationships
    customers = relationship("Customer", back_populates="user", cascade="all, delete-orphan")
    taxes = relationship("Tax", back_populates="user", cascade="all, delete-orphan")
    quotes = relationship("Quote", foreign_keys="Quote.user_id", back_populates="user", cascade="all, delete-orphan")
    sales_person_quotes = relationship("Quote", foreign_keys="Quote.sales_person_id", back_populates="sales_person", cascade="all, delete-orphan")
    invoices = relationship("Invoice", foreign_keys="Invoice.user_id", back_populates="user", cascade="all, delete-orphan")
    created_payments = relationship("Payment", back_populates="creator", cascade="all, delete-orphan")
    packages = relationship("Package", back_populates="user", cascade="all, delete-orphan")
    targets = relationship("Target", back_populates="user", cascade="all, delete-orphan")
    target_achievements = relationship("TargetAchievement", back_populates="user", cascade="all, delete-orphan")
    
    # History relationships
    invoice_history = relationship("InvoiceHistory", back_populates="user", cascade="all, delete-orphan")
    quote_history = relationship("QuoteHistory", back_populates="user", cascade="all, delete-orphan")
    payment_history = relationship("PaymentHistory", back_populates="user", cascade="all, delete-orphan")


class UserActivity(Base):
    """User activity model"""
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(String(50), nullable=False)
    description = Column(String)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="activities")