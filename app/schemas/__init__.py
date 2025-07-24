"""
Pydantic schemas for the XerpeX ERP System
"""
from app.schemas.auth import Token, TokenPayload, UserLogin, UserCreate as AuthUserCreate, UserResponse
from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserInDB, User, 
    UserActivityBase, UserActivityCreate, UserActivity, UserWithActivities
)
from app.schemas.villa import (
    VillaBase, VillaCreate, VillaUpdate, Villa,
    VillaAvailabilityBase, VillaAvailabilityCreate, VillaAvailabilityUpdate, VillaAvailability,
    VillaWithAvailability, AvailabilityCheck, AvailabilityResponse
)
from app.schemas.booking import (
    BookingVillaBase, BookingVillaCreate, BookingVilla,
    BookingPackageBase, BookingPackageCreate, BookingPackage,
    BookingAddonBase, BookingAddonCreate, BookingAddon,
    BookingBase, BookingCreate, BookingUpdate, BookingStatusUpdate,
    Booking, BookingDetail
)
from app.schemas.payment import (
    PaymentBase, PaymentCreate, PaymentUpdate, PaymentStatusUpdate,
    PaymentInvoiceCreate, PaymentInvoiceUpdate, InvoiceResponse,
    PaymentResponse, PaymentDetailResponse
)
from app.schemas.report import (
    ReportDateRangeParams, ReportVillaOccupancyParams, ReportBookingStatusParams, ReportRevenueParams,
    VillaOccupancyItem, VillaOccupancyReport, BookingStatusItem, BookingStatusReport,
    RevenueItem, RevenueReport, TopVillaItem, TopVillasReport, DashboardSummary
)