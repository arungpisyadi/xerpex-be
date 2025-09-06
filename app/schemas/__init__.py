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
    PaymentBase, PaymentCreate, PaymentUpdate, PaymentStatusUpdate, PaymentResponse,
    InvoiceBase, InvoiceCreate, InvoiceUpdate, InvoiceStatusUpdate, InvoiceResponse,
    InvoiceItemBase, InvoiceItemCreate, InvoiceItemUpdate, InvoiceItemResponse,
    QuoteToInvoiceRequest, InvoiceSummary, PaymentSummary, CustomerInvoiceSummary,
    InvoiceStatus, PaymentStatus, PaymentMethod
)
from app.schemas.report import (
    ReportDateRangeParams, ReportVillaOccupancyParams, ReportBookingStatusParams, ReportRevenueParams,
    VillaOccupancyItem, VillaOccupancyReport, BookingStatusItem, BookingStatusReport,
    RevenueItem, RevenueReport, TopVillaItem, TopVillasReport, DashboardSummary
)
from app.schemas.salesmen import (
    SalesmenBase, SalesmenCreate, SalesmenUpdate, SalesmenInDB, Salesmen, SalesmenSummary
)
from app.schemas.survey import (
    SurveyStatus, SurveyPriority, SurveyBase, SurveyCreate, SurveyUpdate, SurveyStatusUpdate,
    SurveyInDB, Survey, SurveyWithSalesman, SurveyStats, SalesmanStats
)
from app.schemas.package import (
    PackageBase, PackageCreate, PackageUpdate, Package
)
from app.schemas.customer import (
    CustomerBase, CustomerCreate, CustomerUpdate, CustomerInDB, Customer,
    CustomerWithQuotes, CustomerWithInvoices
)
from app.schemas.tax import (
    TaxBase, TaxCreate, TaxUpdate, TaxInDB, Tax
)
from app.schemas.quote import (
    QuoteItemBase, QuoteItemCreate, QuoteItemUpdate, QuoteItemInDB, QuoteItem,
    QuoteBase, QuoteCreate, QuoteUpdate, QuoteStatusUpdate, QuoteInDB, Quote,
    QuoteDetail, QuoteSummary, QuoteConversionRequest, QuoteStatus
)
from app.schemas.target import (
    TargetBase, TargetCreate, TargetUpdate, TargetInDB, TargetResponse,
    TargetOverview, MyPerformance, CompanyPerformance
)