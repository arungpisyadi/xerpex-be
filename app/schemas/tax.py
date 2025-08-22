"""
Tax schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, condecimal, validator


class TaxBase(BaseModel):
    """Base tax schema"""
    name: str
    percentage: condecimal(max_digits=5, decimal_places=2)

    @validator('percentage')
    def validate_percentage(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Tax percentage must be between 0 and 100')
        return v


class TaxCreate(TaxBase):
    """Tax creation schema"""
    pass


class TaxUpdate(BaseModel):
    """Tax update schema"""
    name: Optional[str] = None
    percentage: Optional[condecimal(max_digits=5, decimal_places=2)] = None

    @validator('percentage')
    def validate_percentage(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Tax percentage must be between 0 and 100')
        return v


class TaxInDB(TaxBase):
    """Tax in database schema"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class Tax(TaxInDB):
    """Tax schema for API responses"""
    pass