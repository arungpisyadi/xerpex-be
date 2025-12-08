"""
Payment models for the XerpeX ERP System
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Numeric, ForeignKey, CheckConstraint, JSON, Index, func
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    """Payment model"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, nullable=False, default=date.today)
    payment_method = Column(String(50), nullable=False)
    payment_type = Column(String(50), nullable=False)
    reference_number = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    booking = relationship("Booking", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    creator = relationship("User", back_populates="created_payments")
    invoice_history = relationship("InvoiceHistory", back_populates="payment")
    payment_history = relationship("PaymentHistory", back_populates="payment", cascade="all, delete-orphan")
    booking_history = relationship("BookingHistory", back_populates="payment")
    
    # Indexes
    __table_args__ = (
        Index('ix_payments_created_by', 'created_by'),
        Index('ix_payments_booking_id', 'booking_id'),
        Index('ix_payments_payment_type', 'payment_type'),
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )


class Invoice(Base):
    """Invoice model"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sales_person_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="SET NULL"), nullable=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    issue_date = Column(Date, nullable=False, default=date.today)
    due_date = Column(Date, nullable=False)
    check_in = Column(Date, nullable=True)
    check_out = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    payment_terms = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    total = Column(Numeric(10, 2), nullable=False, default=0.00)
    amount_due = Column(Numeric(10, 2), nullable=False, default=0.00)
    tax_total = Column(Numeric(10, 2), nullable=False, default=0.00)
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="invoices")
    sales_person = relationship("User", foreign_keys=[sales_person_id])
    customer = relationship("Customer", back_populates="invoices")
    quote = relationship("Quote", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    villas = relationship("InvoiceVilla", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    history = relationship("InvoiceHistory", back_populates="invoice", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'sent', 'partially_paid', 'paid', 'overdue', 'cancelled')",
            name="check_invoice_status"
        ),
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )


class InvoiceItem(Base):
    """Invoice item model"""
    __tablename__ = "invoice_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False)
    pax = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), nullable=False, default=0.00)
    line_total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    package = relationship("Package", back_populates="invoice_items")
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )


class InvoiceHistory(Base):
    """Invoice history model for tracking invoice lifecycle events"""
    __tablename__ = "invoice_history"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=True)
    event_type = Column(String(50), nullable=False)
    event_category = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)
    event_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="history")
    user = relationship("User", back_populates="invoice_history")
    payment = relationship("Payment", back_populates="invoice_history")
    
    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint(
            "event_category IN ('lifecycle', 'status', 'workflow', 'payment')",
            name="check_invoice_history_event_category"
        ),
        Index('idx_invoice_history_invoice_id', 'invoice_id'),
        Index('idx_invoice_history_created_at_desc', 'created_at'),
        Index('idx_invoice_history_event_category', 'event_category'),
        Index('idx_invoice_history_payment_id', 'payment_id'),
        Index('idx_invoice_history_composite', 'invoice_id', 'created_at', 'event_category'),
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )


class InvoiceVilla(Base):
    """Invoice villa model - simple junction table for invoice-villa associations"""
    __tablename__ = "invoice_villas"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="villas")
    villa = relationship("Villa", back_populates="invoices")
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self):
        return f"<InvoiceVilla(id={self.id}, invoice_id={self.invoice_id}, villa_id={self.villa_id})>"


class PaymentHistory(Base):
    """Payment history model for tracking payment lifecycle events"""
    __tablename__ = "payment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    event_type = Column(String(50), nullable=False)
    event_category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    event_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    payment = relationship("Payment", back_populates="payment_history")
    user = relationship("User", back_populates="payment_history")
    
    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint(
            "event_category IN ('lifecycle', 'status', 'workflow', 'data')",
            name="check_payment_history_event_category"
        ),
        Index('idx_payment_history_payment_id', 'payment_id'),
        Index('idx_payment_history_user_id', 'user_id'),
        Index('idx_payment_history_created_at', 'created_at'),
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )