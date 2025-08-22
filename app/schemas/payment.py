"""
Payment and Invoice schemas for the XerpeX ERP System
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, validator


class InvoiceStatus(str, Enum):
    """Invoice status enumeration"""
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class PaymentMethod(str, Enum):
    """Payment method enumeration"""
    cash = "cash"
    bank_transfer = "bank_transfer"
    credit_card = "credit_card"
    debit_card = "debit_card"
    digital_wallet = "digital_wallet"
    check = "check"
    other = "other"


# Invoice Item Schemas
class InvoiceItemBase(BaseModel):
    """Base invoice item schema"""
    package_id: int
    unit_price: Decimal = Field(..., gt=0, description="Unit price of the item")
    discount: Decimal = Field(default=Decimal('0.00'), ge=0, description="Discount amount")
    line_total: Decimal = Field(..., gt=0, description="Total for this line item")

    @validator('line_total')
    def validate_line_total(cls, v, values):
        """Validate that line_total matches calculation"""
        if 'unit_price' in values and 'discount' in values:
            expected_total = values['unit_price'] - values['discount']
            if abs(v - expected_total) > Decimal('0.01'):
                raise ValueError('line_total must equal unit_price - discount')
        return v


class InvoiceItemCreate(InvoiceItemBase):
    """Invoice item creation schema"""
    pass


class InvoiceItemUpdate(BaseModel):
    """Invoice item update schema"""
    package_id: Optional[int] = None
    unit_price: Optional[Decimal] = Field(None, gt=0)
    discount: Optional[Decimal] = Field(None, ge=0)
    line_total: Optional[Decimal] = Field(None, gt=0)


class InvoiceItemResponse(InvoiceItemBase):
    """Invoice item response schema"""
    id: int
    invoice_id: int
    package_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Invoice Schemas
class InvoiceBase(BaseModel):
    """Base invoice schema"""
    customer_id: int
    issue_date: date = Field(default_factory=date.today)
    due_date: date
    status: InvoiceStatus = InvoiceStatus.draft
    tax_total: Decimal = Field(default=Decimal('0.00'), ge=0)
    notes: Optional[str] = None

    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate that due_date is not before issue_date"""
        if 'issue_date' in values and v < values['issue_date']:
            raise ValueError('due_date cannot be before issue_date')
        return v


class InvoiceCreate(InvoiceBase):
    """Invoice creation schema"""
    items: List[InvoiceItemCreate] = Field(..., min_items=1)
    quote_id: Optional[int] = None  # For quote-to-invoice conversion


class InvoiceUpdate(BaseModel):
    """Invoice update schema"""
    customer_id: Optional[int] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[InvoiceStatus] = None
    tax_total: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = None


class InvoiceStatusUpdate(BaseModel):
    """Invoice status update schema"""
    status: InvoiceStatus


class InvoiceResponse(InvoiceBase):
    """Invoice response schema"""
    id: int
    user_id: int
    invoice_number: str
    quote_id: Optional[int] = None
    total: Decimal
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    items: List[InvoiceItemResponse] = []
    payments: List['PaymentResponse'] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Payment Schemas
class PaymentBase(BaseModel):
    """Base payment schema"""
    invoice_id: int
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod
    payment_date: date = Field(default_factory=date.today)
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Payment creation schema"""
    pass


class PaymentUpdate(BaseModel):
    """Payment update schema"""
    amount: Optional[Decimal] = Field(None, gt=0)
    payment_method: Optional[PaymentMethod] = None
    payment_date: Optional[date] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    """Payment status update schema"""
    status: PaymentStatus


class PaymentResponse(PaymentBase):
    """Payment response schema"""
    id: int
    user_id: int
    status: PaymentStatus
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Quote to Invoice Conversion
class QuoteToInvoiceRequest(BaseModel):
    """Quote to invoice conversion request schema"""
    quote_id: int
    issue_date: Optional[date] = Field(default_factory=date.today)
    due_date: date
    notes: Optional[str] = None


# Summary and Statistics Schemas
class InvoiceSummary(BaseModel):
    """Invoice summary schema"""
    total_invoices: int
    total_value: Decimal
    status_breakdown: dict
    overdue_count: int
    overdue_value: Decimal


class PaymentSummary(BaseModel):
    """Payment summary schema"""
    total_payments: int
    total_amount: Decimal
    method_breakdown: dict
    recent_payments: List[PaymentResponse]


class CustomerInvoiceSummary(BaseModel):
    """Customer invoice summary schema"""
    customer_id: int
    customer_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal
    invoice_count: int
    last_payment_date: Optional[date] = None


# Update forward references
InvoiceResponse.model_rebuild()