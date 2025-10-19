"""
Villa schemas for the XerpeX ERP System
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, condecimal


class VillaBase(BaseModel):
    """Base villa schema"""
    name: str
    description: Optional[str] = None
    capacity: str
    room_type: str
    base_price: condecimal(max_digits=10, decimal_places=2)
    is_active: bool = True


class VillaCreate(VillaBase):
    """Villa creation schema"""
    pass


class VillaUpdate(BaseModel):
    """Villa update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[str] = None
    room_type: Optional[str] = None
    base_price: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    is_active: Optional[bool] = None


class Villa(VillaBase):
    """Villa schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class VillaAvailabilityBase(BaseModel):
    """Base villa availability schema"""
    date: date
    is_available: bool = True
    blocked_reason: Optional[str] = None


class VillaAvailabilityCreate(VillaAvailabilityBase):
    """Villa availability creation schema"""
    villa_id: int


class VillaAvailabilityUpdate(BaseModel):
    """Villa availability update schema"""
    is_available: Optional[bool] = None
    blocked_reason: Optional[str] = None


class VillaAvailability(VillaAvailabilityBase):
    """Villa availability schema"""
    id: int
    villa_id: int
    updated_by: Optional[int] = None
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class VillaWithAvailability(Villa):
    """Villa with availability schema"""
    availabilities: List[VillaAvailability] = []


class AvailabilityCheck(BaseModel):
    """Availability check schema"""
    villa_id: Optional[int] = None
    check_in: date
    check_out: date


class AvailabilityResponse(BaseModel):
    """Availability response schema"""
    is_available: bool
    villa_id: Optional[int] = None
    unavailable_dates: Optional[List[date]] = None


class VillaListResponse(BaseModel):
    """Response schema for villa list endpoint"""
    villas: List[Villa]
    total: int
    skip: int
    limit: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class VillaResponse(Villa):
    """Villa response schema for API responses"""
    pass