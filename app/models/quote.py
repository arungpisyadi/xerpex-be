"""
Quote models for the XerpeX ERP System
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Numeric, ForeignKey, CheckConstraint, JSON, Index, func
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
    check_in = Column(Date, nullable=True)
    check_out = Column(Date, nullable=True)
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
    villas = relationship("QuoteVilla", back_populates="quote", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="quote")
    history = relationship("QuoteHistory", back_populates="quote", cascade="all, delete-orphan")
    
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


class QuoteVilla(Base):
    """Quote villa model - simple junction table for quote-villa associations"""
    __tablename__ = "quote_villas"
    
    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    villa_id = Column(Integer, ForeignKey("villas.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    quote = relationship("Quote", back_populates="villas")
    villa = relationship("Villa", back_populates="quotes")
    
    # Constraints
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self):
        return f"<QuoteVilla(id={self.id}, quote_id={self.quote_id}, villa_id={self.villa_id})>"


class QuoteHistory(Base):
    """Quote history model for tracking quote lifecycle events"""
    __tablename__ = "quote_history"
    
    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    event_type = Column(String(50), nullable=False)
    event_category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    event_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    quote = relationship("Quote", back_populates="history")
    user = relationship("User", back_populates="quote_history")
    
    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint(
            "event_category IN ('lifecycle', 'status', 'workflow', 'data')",
            name="check_quote_history_event_category"
        ),
        Index('idx_quote_history_quote_id', 'quote_id'),
        Index('idx_quote_history_user_id', 'user_id'),
        Index('idx_quote_history_created_at', 'created_at'),
        {"sqlite_autoincrement": True},  # For SQLite compatibility
    )