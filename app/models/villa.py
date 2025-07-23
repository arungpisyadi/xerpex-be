"""
Villa models for the XerpeX ERP System
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Villa(Base):
    """Villa model"""
    __tablename__ = "villas"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    capacity = Column(Integer, nullable=False)
    room_type = Column(String(50), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    availabilities = relationship("VillaAvailability", back_populates="villa", cascade="all, delete-orphan")
    bookings = relationship("BookingVilla", back_populates="villa")


class VillaAvailability(Base):
    """Villa availability model"""
    __tablename__ = "villa_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    is_available = Column(Boolean, default=True)
    blocked_reason = Column(Text)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    villa = relationship("Villa", back_populates="availabilities")
    updated_by_user = relationship("User", back_populates="updated_availabilities")
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )