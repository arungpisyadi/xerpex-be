"""
KPI API controllers for the XerpeX ERP System
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.kpi import KPIResponse
from app.schemas.revenue import MonthlyRevenueResponse, CurrentMonthPerformanceResponse, CurrentYearPerformanceResponse
from app.services.kpi import KPIService
from app.services.revenue import RevenueService
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get("/customers", response_model=KPIResponse)
async def get_customers_kpi_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get customer KPI data with current vs previous month comparison
    """
    try:
        return KPIService.get_customers_kpi(db=db, current_user=current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving customer KPI: {str(e)}"
        )


@router.get("/bookings", response_model=KPIResponse)
async def get_bookings_kpi_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get booking KPI data with current vs previous month comparison
    """
    try:
        return KPIService.get_bookings_kpi(db=db, current_user=current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving booking KPI: {str(e)}"
        )


@router.get("/surveys", response_model=KPIResponse)
async def get_surveys_kpi_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get survey KPI data with current vs previous month comparison
    """
    try:
        return KPIService.get_surveys_kpi(db=db, current_user=current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving survey KPI: {str(e)}"
        )


@router.get("/quotes", response_model=KPIResponse)
async def get_quotes_kpi_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get quote KPI data with current vs previous month comparison
    """
    try:
        return KPIService.get_quotes_kpi(db=db, current_user=current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving quote KPI: {str(e)}"
        )


@router.get("/monthly_revenue", response_model=MonthlyRevenueResponse)
async def get_monthly_revenue_endpoint(
    year: int = Query(default=None, description="Year for revenue data (defaults to current year)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get monthly revenue data for the specified year with user isolation.
    Sales users see only their data, admin/finance see all data.
    """
    try:
        # Default to current year if not specified
        if year is None:
            year = datetime.now().year
        
        # Validate year range
        current_year = datetime.now().year
        if year < 2000 or year > current_year + 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Year must be between 2000 and {current_year + 5}"
            )
        
        revenue_service = RevenueService(db)
        return revenue_service.get_monthly_revenue_with_user_isolation(year, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving monthly revenue: {str(e)}"
        )


@router.get("/current_month_performance", response_model=CurrentMonthPerformanceResponse)
async def get_current_month_performance_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current month performance data with target vs achievement comparison.
    Shows current month target, achieved revenue from paid invoices, today's revenue,
    performance percentage, and days remaining in month.
    Sales users see only their data, admin/finance see all data.
    """
    try:
        revenue_service = RevenueService(db)
        return revenue_service.get_current_month_performance(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving current month performance: {str(e)}"
        )


@router.get("/current_year_performance", response_model=CurrentYearPerformanceResponse)
async def get_current_year_performance_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current year performance data with target vs achievement comparison.
    Shows current year target (sum of all months), achieved revenue from paid invoices (year-to-date),
    performance percentage, and months completed in the current year.
    Sales users see only their data, admin/finance see all data.
    """
    try:
        revenue_service = RevenueService(db)
        return revenue_service.get_current_year_performance(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving current year performance: {str(e)}"
        )