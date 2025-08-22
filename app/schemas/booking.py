"""
Booking schemas for the XerpeX ERP System
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, condecimal, Field, field_validator

from app.utils.helpers import sanitize_phone_number


class BookingVillaBase(BaseModel):
    """Base booking villa schema"""
    villa_id: int


class BookingVillaCreate(BookingVillaBase):
    """Booking villa creation schema"""
    pass


class BookingVilla(BookingVillaBase):
    """Booking villa schema"""
    id: int
    booking_id: int
    assigned_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingPackageBase(BaseModel):
    """Base booking package schema"""
    package_name: str
    package_price: condecimal(max_digits=10, decimal_places=2)
    notes: Optional[str] = None


class BookingPackageCreate(BookingPackageBase):
    """Booking package creation schema"""
    pass


class BookingPackage(BookingPackageBase):
    """Booking package schema"""
    id: int
    booking_id: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingAddonBase(BaseModel):
    """Base booking addon schema"""
    service_name: str
    service_price: condecimal(max_digits=10, decimal_places=2)
    quantity: int = 1


class BookingAddonCreate(BookingAddonBase):
    """Booking addon creation schema"""
    pass


class BookingAddon(BookingAddonBase):
    """Booking addon schema"""
    id: int
    booking_id: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingBase(BaseModel):
    """Base booking schema"""
    guest_name: str
    guest_email: Optional[EmailStr] = None
    guest_phone: Optional[str] = None
    check_in: date
    check_out: date
    total_pax: int
    notes: Optional[str] = None


class BookingCreate(BookingBase):
    """Booking creation schema"""
    villas: List[BookingVillaCreate]
    packages: Optional[List[BookingPackageCreate]] = None
    addons: Optional[List[BookingAddonCreate]] = None
    
    @field_validator('guest_phone')
    @classmethod
    def validate_phone_number(cls, v):
        return sanitize_phone_number(v)


class BookingUpdate(BaseModel):
    """Booking update schema"""
    guest_name: Optional[str] = None
    guest_email: Optional[EmailStr] = None
    guest_phone: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    total_pax: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    
    @field_validator('guest_phone')
    @classmethod
    def validate_phone_number(cls, v):
        return sanitize_phone_number(v)


class BookingStatusUpdate(BaseModel):
    """Booking status update schema"""
    status: str = Field(..., description="Booking status (pending, confirmed, ongoing, completed, cancelled)")


class Booking(BookingBase):
    """Booking schema"""
    id: int
    booking_code: str
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    villas: List[BookingVilla] = []
    packages: List[BookingPackage] = []
    addons: List[BookingAddon] = []

    class Config:
        """Pydantic config"""
        from_attributes = True


class BookingDetail(Booking):
    """Booking detail schema"""
    total_price: condecimal(max_digits=10, decimal_places=2)
    total_paid: condecimal(max_digits=10, decimal_places=2)
    balance: condecimal(max_digits=10, decimal_places=2)


class BookingResponse(Booking):
    """Booking response schema for API"""
    pass


class BookingDetailResponse(BookingDetail):
    """Booking detail response schema for API"""
    pass


class BookingVillaResponse(BookingVilla):
    """Booking villa response schema for API"""
    pass


class BookingPackageResponse(BookingPackage):
    """Booking package response schema for API"""
    pass


class BookingAddonResponse(BookingAddon):
    """Booking addon response schema for API"""
    pass


class BookingListResponse(BaseModel):
    """Response schema for booking list endpoint"""
    bookings: List[BookingResponse]
    total: int
    skip: int
    limit: int

    class Config:
        """Pydantic config"""
        from_attributes = True