"""
Salesmen schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator

from app.utils.helpers import sanitize_phone_number


class SalesmenBase(BaseModel):
    """Base salesmen schema"""
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    is_active: bool = True


class SalesmenCreate(SalesmenBase):
    """Salesmen creation schema"""
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        return sanitize_phone_number(v)


class SalesmenUpdate(BaseModel):
    """Salesmen update schema"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        return sanitize_phone_number(v)


class SalesmenInDB(SalesmenBase):
    """Salesmen in database schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class SalesmenListResponse(BaseModel):
    """Response schema for salesmen list endpoint"""
    salesmen: List["Salesmen"]
    total: int
    skip: int
    limit: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class SalesmenResponse(BaseModel):
    """Salesmen response schema for API responses"""
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    is_active: bool = True
    full_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class Salesmen(SalesmenInDB):
    """Salesmen schema"""
    full_name: str

    class Config:
        """Pydantic config"""
        from_attributes = True


class SalesmenSummary(BaseModel):
    """Salesmen summary schema for dropdowns"""
    id: int
    full_name: str
    email: EmailStr
    is_active: bool

    class Config:
        """Pydantic config"""
        from_attributes = True