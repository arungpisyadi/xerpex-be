"""
Quote models for the XerpeX ERP System
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Quote(Base):
    """Quote model for quotation system"""
    __tablename__ = "quotes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    sales_person_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    quote_number = Column(String(50), unique=True, nullable=False, index=True)
    issue_date = Column(Date, nullable=False, default=date.today)
    expiry_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    notes = Column(Text, nullable=True)
    total = Column(Numeric(10, 2), nullable=False, default=0.00)
    tax_total = Column(Numeric(10, 2), nullable=False, default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys="Quote.user_id", back_populates="quotes")
    customer = relationship("Customer", back_populates="quotes")
    sales_person = relationship("User", foreign_keys=[sales_person_id], back_populates="sales_person_quotes")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="quote")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'sent', 'accepted', 'declined', 'expired')",
            name="check_quote_status"
        ),
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )


class QuoteItem(Base):
    """Quote item model for quote line items"""
    __tablename__ = "quote_items"
    
    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False)
    pax = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), nullable=False, default=0.00)
    line_total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    quote = relationship("Quote", back_populates="items")
    package = relationship("Package", back_populates="quote_items")
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )