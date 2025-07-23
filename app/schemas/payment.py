"""
Payment schemas for the XerpeX ERP System
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, EmailStr


class PaymentBase(BaseModel):
    """Base payment schema"""
    booking_id: int
    amount: Decimal = Field(..., gt=0)
    payment_method: str
    payment_date: datetime
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Payment creation schema"""
    pass


class PaymentUpdate(BaseModel):
    """Payment update schema"""
    amount: Optional[Decimal] = Field(None, gt=0)
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    """Payment status update schema"""
    status: str = Field(..., description="Payment status (pending, paid, failed, refunded)")


class PaymentInvoiceCreate(BaseModel):
    """Payment invoice creation schema"""
    booking_id: int
    guest_name: str
    guest_email: EmailStr
    guest_phone: str
    due_date: datetime
    items: List[dict]
    notes: Optional[str] = None


class PaymentInvoiceUpdate(BaseModel):
    """Payment invoice update schema"""
    guest_name: Optional[str] = None
    guest_email: Optional[EmailStr] = None
    guest_phone: Optional[str] = None
    due_date: Optional[datetime] = None
    items: Optional[List[dict]] = None
    notes: Optional[str] = None


class PaymentInvoiceResponse(BaseModel):
    """Payment invoice response schema"""
    id: int
    invoice_number: str
    booking_id: int
    guest_name: str
    guest_email: EmailStr
    guest_phone: str
    due_date: datetime
    total_amount: Decimal
    status: str
    items: List[dict]
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        orm_mode = True


class PaymentResponse(BaseModel):
    """Payment response schema"""
    id: int
    booking_id: int
    invoice_id: Optional[int] = None
    amount: Decimal
    payment_method: str
    payment_date: datetime
    status: str
    transaction_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        orm_mode = True


class PaymentDetailResponse(BaseModel):
    """Payment detail response schema"""
    payment: PaymentResponse
    invoice: Optional[PaymentInvoiceResponse] = None
    booking_code: str
    guest_name: str

    class Config:
        """Pydantic config"""
        orm_mode = True