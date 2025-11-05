"""
Booking models for the XerpeX ERP System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Booking(Base):
    """Booking model for accommodation booking system"""
    __tablename__ = "bookings"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    sales_person_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Booking Identifiers
    booking_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Dates
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    
    # Status
    status = Column(String(20), nullable=False, default="pending")
    
    # Additional Information
    total_pax = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    
    # Financial Fields
    total = Column(Numeric(15, 2), nullable=False, default=0.00)
    tax_total = Column(Numeric(15, 2), nullable=False, default=0.00)
    amount_paid = Column(Numeric(15, 2), nullable=False, default=0.00)
    amount_due = Column(Numeric(15, 2), nullable=False, default=0.00)
    
    # Audit Fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="bookings")
    customer = relationship("Customer", back_populates="bookings")
    sales_person = relationship("User", foreign_keys=[sales_person_id], back_populates="sales_person_bookings")
    items = relationship("BookingItem", back_populates="booking", cascade="all, delete-orphan")
    villas = relationship("BookingVilla", back_populates="booking", cascade="all, delete-orphan")
    history = relationship("BookingHistory", back_populates="booking", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'checked_in', 'checked_out', 'completed', 'cancelled')",
            name="check_booking_status"
        ),
        CheckConstraint(
            "check_out > check_in",
            name="check_booking_dates"
        ),
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self):
        return f"<Booking(id={self.id}, booking_code='{self.booking_code}', status='{self.status}')>"


class BookingItem(Base):
    """Booking item model for booking line items"""
    __tablename__ = "booking_items"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False)
    pax = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(15, 2), nullable=False)
    discount = Column(Numeric(15, 2), nullable=False, default=0.00)
    line_total = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = relationship("Booking", back_populates="items")
    package = relationship("Package", back_populates="booking_items")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("pax >= 1", name="check_booking_item_pax"),
        CheckConstraint("unit_price >= 0", name="check_booking_item_unit_price"),
        CheckConstraint("discount >= 0", name="check_booking_item_discount"),
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self):
        return f"<BookingItem(id={self.id}, booking_id={self.booking_id}, package_id={self.package_id}, pax={self.pax})>"


class BookingVilla(Base):
    """Booking villa model - simple junction table for booking-villa associations"""
    __tablename__ = "booking_villas"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="villas")
    villa = relationship("Villa", back_populates="bookings")
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self):
        return f"<BookingVilla(id={self.id}, booking_id={self.booking_id}, villa_id={self.villa_id})>"


class BookingHistory(Base):
    """Booking history model for audit trail"""
    __tablename__ = "booking_history"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    booking = relationship("Booking", back_populates="history")
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('created', 'status_change', 'field_update', 'item_added', " +
            "'item_removed', 'villa_added', 'villa_removed', 'payment_received')",
            name="check_booking_history_change_type"
        ),
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self):
        return f"<BookingHistory(id={self.id}, booking_id={self.booking_id}, change_type='{self.change_type}')>"