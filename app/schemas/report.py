"""
Report schemas for the XerpeX ERP System
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


class ReportDateRangeParams(BaseModel):
    """Report date range parameters"""
    start_date: date
    end_date: date


class ReportVillaOccupancyParams(ReportDateRangeParams):
    """Villa occupancy report parameters"""
    villa_id: Optional[int] = None


class ReportBookingStatusParams(ReportDateRangeParams):
    """Booking status report parameters"""
    status: Optional[str] = None


class ReportRevenueParams(ReportDateRangeParams):
    """Revenue report parameters"""
    group_by: str = Field(..., description="Group by: 'day', 'week', 'month', 'year', 'villa'")
    villa_id: Optional[int] = None


class VillaOccupancyItem(BaseModel):
    """Villa occupancy item"""
    villa_id: int
    villa_name: str
    total_days: int
    occupied_days: int
    occupancy_rate: float
    revenue: Decimal


class VillaOccupancyReport(BaseModel):
    """Villa occupancy report"""
    start_date: date
    end_date: date
    total_days: int
    villas: List[VillaOccupancyItem]
    average_occupancy_rate: float
    total_revenue: Decimal


class BookingStatusItem(BaseModel):
    """Booking status item"""
    status: str
    count: int
    percentage: float


class BookingStatusReport(BaseModel):
    """Booking status report"""
    start_date: date
    end_date: date
    total_bookings: int
    status_breakdown: List[BookingStatusItem]


class RevenueItem(BaseModel):
    """Revenue item"""
    period: str
    revenue: Decimal
    bookings_count: int
    average_booking_value: Decimal


class RevenueReport(BaseModel):
    """Revenue report"""
    start_date: date
    end_date: date
    group_by: str
    total_revenue: Decimal
    total_bookings: int
    average_booking_value: Decimal
    items: List[RevenueItem]


class TopVillaItem(BaseModel):
    """Top villa item"""
    villa_id: int
    villa_name: str
    bookings_count: int
    revenue: Decimal
    occupancy_rate: float


class TopVillasReport(BaseModel):
    """Top villas report"""
    start_date: date
    end_date: date
    villas: List[TopVillaItem]


class DashboardSummary(BaseModel):
    """Dashboard summary"""
    total_bookings: int
    pending_bookings: int
    ongoing_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_revenue: Decimal
    pending_payments: Decimal
    occupancy_rate: float
    top_villas: List[Dict[str, Any]]
    recent_bookings: List[Dict[str, Any]]
    revenue_chart: List[Dict[str, Any]]


# =====================================================
# Sales Report Schemas
# =====================================================


class SalesReportParams(BaseModel):
    """Sales report input parameters"""
    start_date: date
    end_date: date
    sales_person_ids: Optional[List[int]] = None
    payment_status: Optional[str] = None

    @field_validator('sales_person_ids', mode='before')
    @classmethod
    def validate_sales_person_ids(cls, v):
        """Handle null or empty list values"""
        if v is None or v == []:
            return None
        # Filter out any None values in the list
        if isinstance(v, list):
            return [item for item in v if item is not None]
        return v


class SalesReportItem(BaseModel):
    """Individual sales report row data"""
    invoice_id: int
    invoice_number: str
    booking_id: Optional[int] = None
    booking_code: Optional[str] = None
    customer_name: str
    sales_person_name: Optional[str]
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    payment_status: str


class SalesReport(BaseModel):
    """Full sales report response"""
    start_date: date
    end_date: date
    items: List[SalesReportItem]
    total_sales_amount: Decimal
    total_paid_amount: Decimal
    total_difference: Decimal