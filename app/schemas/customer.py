"""
Customer schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator

from app.utils.helpers import sanitize_phone_number


class CustomerBase(BaseModel):
    """Base customer schema"""
    name: str
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    billing_address: Optional[str] = None
    status: Optional[int] = 1  # 1 = active, 0 = inactive


class CustomerCreate(CustomerBase):
    """Customer creation schema"""
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize phone number using helper function"""
        if v is None:
            return v
        return sanitize_phone_number(v)


class CustomerUpdate(BaseModel):
    """Customer update schema"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    billing_address: Optional[str] = None
    status: Optional[int] = None
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize phone number using helper function"""
        if v is None:
            return v
        return sanitize_phone_number(v)


class CustomerInDB(CustomerBase):
    """Customer in database schema"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class CustomerResponse(CustomerInDB):
    """Customer response schema for API responses"""
    pass


class Customer(CustomerInDB):
    """Customer schema for API responses (backward compatibility)"""
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


class CustomerListResponse(BaseModel):
    """Response schema for customer list endpoint"""
    customers: List[CustomerResponse]
    total: int
    skip: int
    limit: int

    class Config:
        """Pydantic config"""
        from_attributes = True