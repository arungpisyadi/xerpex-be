"""
Booking schemas for the XerpeX ERP System
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List, Literal, Dict, Any
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, EmailStr, condecimal, Field, field_validator, model_validator

from app.utils.helpers import sanitize_phone_number
from app.schemas.customer import Customer
from app.schemas.package import Package
from app.schemas.villa import Villa
from app.schemas.user import UserResponse


# Booking status enum
class BookingStatus(str, Enum):
    """Booking status enumeration"""
    pending = "pending"
    confirmed = "confirmed"
    checked_in = "checked_in"
    checked_out = "checked_out"
    completed = "completed"
    cancelled = "cancelled"


# Booking change types for history
BookingChangeType = Literal[
    'created', 'status_change', 'field_update', 'item_added',
    'item_removed', 'villa_added', 'villa_removed', 'payment_received'
]


# ============================================================================
# Booking Item Schemas
# ============================================================================

class BookingItemBase(BaseModel):
    """Base booking item schema"""
    package_id: int
    unit_price: condecimal(max_digits=15, decimal_places=2)
    discount: condecimal(max_digits=15, decimal_places=2) = Decimal('0.00')
    pax: int = 1
    line_total: condecimal(max_digits=15, decimal_places=2)

    @field_validator('pax')
    @classmethod
    def validate_pax(cls, v):
        if v < 1:
            raise ValueError('pax must be at least 1')
        return v

    @field_validator('unit_price', 'discount', 'line_total')
    @classmethod
    def validate_amounts(cls, v):
        if v < 0:
            raise ValueError('amounts must be non-negative')
        return v


class BookingItemCreate(BookingItemBase):
    """Booking item creation schema"""
    pass


class BookingItemUpdate(BaseModel):
    """Booking item update schema"""
    package_id: Optional[int] = None
    unit_price: Optional[condecimal(max_digits=15, decimal_places=2)] = None
    discount: Optional[condecimal(max_digits=15, decimal_places=2)] = None
    pax: Optional[int] = None
    line_total: Optional[condecimal(max_digits=15, decimal_places=2)] = None

    @field_validator('pax')
    @classmethod
    def validate_pax(cls, v):
        if v is not None and v < 1:
            raise ValueError('pax must be at least 1')
        return v

    @field_validator('unit_price', 'discount', 'line_total')
    @classmethod
    def validate_amounts(cls, v):
        if v is not None and v < 0:
            raise ValueError('amounts must be non-negative')
        return v


class BookingItemInDB(BookingItemBase):
    """Booking item in database schema"""
    id: int
    booking_id: int
    created_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingItem(BookingItemInDB):
    """Booking item schema for API responses"""
    package: Optional[Package] = None  # Will be populated with Package schema

    class Config:
        """Pydantic config"""
        from_attributes = True


# ============================================================================
# Booking History Schemas
# ============================================================================

class BookingHistoryBase(BaseModel):
    """Base booking history schema"""
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_type: BookingChangeType


class BookingHistoryCreate(BookingHistoryBase):
    """Booking history creation schema"""
    booking_id: int
    user_id: int


class BookingHistory(BookingHistoryBase):
    """Booking history schema"""
    id: int
    booking_id: int
    user_id: int
    created_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingHistoryResponse(BaseModel):
    """Booking history response schema for API"""
    id: int
    booking_id: int
    user_id: Optional[int]
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_type: str
    payment_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        """Pydantic config"""
        from_attributes = True


# ============================================================================
# Booking Villa Schemas
# ============================================================================

class BookingVillaBase(BaseModel):
    """Base booking villa schema - simple junction table"""
    villa_id: int


class BookingVillaCreate(BookingVillaBase):
    """Booking villa creation schema"""
    pass


class BookingVillaInDB(BookingVillaBase):
    """Booking villa in database schema"""
    id: int
    booking_id: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingVilla(BookingVillaInDB):
    """Booking villa schema for API responses"""
    villa: Optional[Villa] = None  # Will be populated with Villa schema

    class Config:
        """Pydantic config"""
        from_attributes = True


# ============================================================================
# Main Booking Schemas
# ============================================================================

class BookingBase(BaseModel):
    """Base booking schema"""
    customer_id: int
    check_in: date
    check_out: date
    total_pax: int = 1
    status: BookingStatus = BookingStatus.pending
    notes: Optional[str] = None
    sales_person_id: Optional[int] = None

    @model_validator(mode='after')
    def validate_dates(self):
        """Validate that check_out is on or after check_in"""
        if self.check_out < self.check_in:
            raise ValueError('Check-out date must be on or after check-in date')
        return self

    @field_validator('check_out')
    @classmethod
    def validate_check_out(cls, v, info):
        if 'check_in' in info.data and v < info.data['check_in']:
            raise ValueError('Check-out date must be on or after check-in date')
        return v

    @field_validator('total_pax')
    @classmethod
    def validate_total_pax(cls, v):
        if v < 1:
            raise ValueError('total_pax must be at least 1')
        return v


class BookingCreate(BookingBase):
    """Booking creation schema"""
    villas: List[int] = []
    items: List[BookingItemCreate] = []
    
    @field_validator('villas')
    @classmethod
    def validate_unique_villas(cls, v):
        """Ensure villas are unique"""
        if len(v) != len(set(v)):
            raise ValueError('villas must be unique')
        return v


class BookingUpdate(BaseModel):
    """Booking update schema"""
    customer_id: Optional[int] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    total_pax: Optional[int] = None
    status: Optional[BookingStatus] = None
    notes: Optional[str] = None
    sales_person_id: Optional[int] = None
    items: Optional[List[BookingItemCreate]] = None

    @model_validator(mode='after')
    def validate_dates(self):
        """Validate that check_out is on or after check_in"""
        if self.check_out is not None and self.check_in is not None:
            if self.check_out < self.check_in:
                raise ValueError('Check-out date must be on or after check-in date')
        return self

    @field_validator('check_out')
    @classmethod
    def validate_check_out(cls, v, info):
        if v is not None and 'check_in' in info.data and info.data['check_in'] is not None:
            if v < info.data['check_in']:
                raise ValueError('Check-out date must be on or after check-in date')
        return v

    @field_validator('total_pax')
    @classmethod
    def validate_total_pax(cls, v):
        if v is not None and v < 1:
            raise ValueError('total_pax must be at least 1')
        return v


class BookingStatusUpdate(BaseModel):
    """Booking status update schema"""
    status: BookingStatus = Field(..., description="Booking status (pending, confirmed, checked_in, checked_out, completed, cancelled)")


class BookingInDB(BookingBase):
    """Booking in database schema"""
    id: int
    user_id: int
    booking_code: str
    total: condecimal(max_digits=15, decimal_places=2)
    tax_total: condecimal(max_digits=15, decimal_places=2)
    amount_paid: condecimal(max_digits=15, decimal_places=2)
    amount_due: condecimal(max_digits=15, decimal_places=2)
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class Booking(BookingInDB):
    """Booking schema for API responses"""
    customer: Optional[Customer] = None  # Customer schema
    sales_person: Optional[UserResponse] = None  # Sales person who handled this booking
    items: List[BookingItem] = []
    villas: List[BookingVilla] = []
    history: Optional[List[BookingHistoryResponse]] = []

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingDetail(Booking):
    """Detailed booking schema with history"""
    history: List[BookingHistory] = []

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingSummary(BaseModel):
    """Booking summary schema for lists"""
    id: int
    booking_code: str
    customer_name: str
    check_in: date
    check_out: date
    status: BookingStatus
    total: condecimal(max_digits=15, decimal_places=2)
    amount_due: condecimal(max_digits=15, decimal_places=2)
    created_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingListResponse(BaseModel):
    """Response schema for booking list endpoint"""
    bookings: List[Booking]
    total: int
    skip: int
    limit: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingCalculationResponse(BaseModel):
    """Response schema for booking calculation endpoint"""
    subtotal: condecimal(max_digits=15, decimal_places=2)
    tax_total: condecimal(max_digits=15, decimal_places=2)
    total: condecimal(max_digits=15, decimal_places=2)
    taxes_applied: List[dict] = []

    class Config:
        """Pydantic config"""
        from_attributes = True


# Legacy response schemas for backward compatibility
class BookingResponse(Booking):
    """Booking response schema for API"""
    pass


class BookingDetailResponse(BookingDetail):
    """Booking detail response schema for API"""
    pass


class BookingVillaResponse(BookingVilla):
    """Booking villa response schema for API"""
    pass