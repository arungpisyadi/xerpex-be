"""
Salesmen schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class SalesmenBase(BaseModel):
    """Base salesmen schema"""
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    is_active: bool = True


class SalesmenCreate(SalesmenBase):
    """Salesmen creation schema"""
    pass


class SalesmenUpdate(BaseModel):
    """Salesmen update schema"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None


class SalesmenInDB(SalesmenBase):
    """Salesmen in database schema"""
    id: int
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