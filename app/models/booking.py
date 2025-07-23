"""
Booking models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Booking(Base):
    """Booking model"""
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_code = Column(String(20), unique=True, nullable=False, index=True)
    guest_name = Column(String(100), nullable=False)
    guest_email = Column(String(100))
    guest_phone = Column(String(20))
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    total_pax = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    villas = relationship("BookingVilla", back_populates="booking", cascade="all, delete-orphan")
    packages = relationship("BookingPackage", back_populates="booking", cascade="all, delete-orphan")
    addons = relationship("BookingAddon", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="booking", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_bookings")


class BookingVilla(Base):
    """Booking villa model"""
    __tablename__ = "booking_villas"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = relationship("Booking", back_populates="villas")
    villa = relationship("Villa", back_populates="bookings")


class BookingPackage(Base):
    """Booking package model"""
    __tablename__ = "booking_packages"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    package_name = Column(String(100), nullable=False)
    package_price = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text)
    
    # Relationships
    booking = relationship("Booking", back_populates="packages")


class BookingAddon(Base):
    """Booking addon model"""
    __tablename__ = "booking_addons"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    service_name = Column(String(100), nullable=False)
    service_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, default=1)
    
    # Relationships
    booking = relationship("Booking", back_populates="addons")