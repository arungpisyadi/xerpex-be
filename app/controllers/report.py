"""
Report controller for the XerpeX ERP System
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.report import (
    ReportVillaOccupancyParams, ReportBookingStatusParams, ReportRevenueParams,
    VillaOccupancyReport, BookingStatusReport, RevenueReport,
    TopVillasReport, DashboardSummary
)
from app.services.report import (
    get_villa_occupancy_report, get_booking_status_report,
    get_revenue_report, get_top_villas_report, get_dashboard_summary
)
from app.utils.security import get_current_active_user, get_current_admin_user


router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_active_user)]
)


@router.get("/dashboard", response_model=DashboardSummary)
def read_dashboard_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get dashboard summary
    """
    return get_dashboard_summary(db)


@router.post("/villa-occupancy", response_model=VillaOccupancyReport)
def read_villa_occupancy_report(
    params: ReportVillaOccupancyParams,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get villa occupancy report
    """
    return get_villa_occupancy_report(db, params)


@router.post("/booking-status", response_model=BookingStatusReport)
def read_booking_status_report(
    params: ReportBookingStatusParams,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get booking status report
    """
    return get_booking_status_report(db, params)


@router.post("/revenue", response_model=RevenueReport)
def read_revenue_report(
    params: ReportRevenueParams,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get revenue report
    """
    return get_revenue_report(db, params)


@router.get("/top-villas", response_model=TopVillasReport)
def read_top_villas_report(
    start_date: date,
    end_date: date,
    limit: Optional[int] = 5,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get top villas report
    """
    return get_top_villas_report(db, start_date, end_date, limit)