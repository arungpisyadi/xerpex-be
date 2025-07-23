"""
Report schemas for the XerpeX ERP System
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


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