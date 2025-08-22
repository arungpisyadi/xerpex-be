"""
Customer schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class CustomerBase(BaseModel):
    """Base customer schema"""
    name: str
    email: Optional[EmailStr] = None
    billing_address: Optional[str] = None


class CustomerCreate(CustomerBase):
    """Customer creation schema"""
    pass


class CustomerUpdate(BaseModel):
    """Customer update schema"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    billing_address: Optional[str] = None


class CustomerInDB(CustomerBase):
    """Customer in database schema"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class Customer(CustomerInDB):
    """Customer schema for API responses"""
    pass


class CustomerWithQuotes(Customer):
    """Customer schema with related quotes"""
    quotes: list = []

    class Config:
        """Pydantic config"""
        from_attributes = True


class CustomerWithInvoices(Customer):
    """Customer schema with related invoices"""
    invoices: list = []

    class Config:
        """Pydantic config"""
        from_attributes = True