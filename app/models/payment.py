"""
Payment models for the XerpeX ERP System
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    """Payment model"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, nullable=False, default=date.today)
    payment_mode = Column(String(50), nullable=False)
    reference_number = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )


class Invoice(Base):
    """Invoice model"""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="SET NULL"), nullable=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    issue_date = Column(Date, nullable=False, default=date.today)
    due_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    payment_terms = Column(String(50), nullable=True)
    total = Column(Numeric(10, 2), nullable=False, default=0.00)
    amount_due = Column(Numeric(10, 2), nullable=False, default=0.00)
    tax_total = Column(Numeric(10, 2), nullable=False, default=0.00)
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    quote = relationship("Quote", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    
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