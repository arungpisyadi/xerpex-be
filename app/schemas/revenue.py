"""
Revenue schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class MonthlyRevenueData(BaseModel):
    """Monthly revenue data schema"""
    month: int = Field(..., ge=1, le=12, description="Month number (1-12)")
    month_name: str = Field(..., description="Month name (e.g., 'January')")
    revenue: float = Field(..., description="Revenue amount for the month")

    class Config:
        """Pydantic config"""
        from_attributes = True
        json_encoders = {
            float: lambda v: round(v, 2) if v is not None else 0.0
        }


class MonthlyRevenueResponse(BaseModel):
    """Monthly revenue response schema for GET /revenue/monthly"""
    year: int = Field(..., description="Year for the revenue data")
    monthly_data: List[float] = Field(..., description="Array of 12 revenue amounts ordered by month (Jan-Dec)")
    total_yearly_revenue: float = Field(..., description="Total revenue for the entire year")
    currency: str = Field(default="IDR", description="Currency code")
    period: str = Field(..., description="Year period (e.g., '2025')")

    class Config:
        """Pydantic config"""
        from_attributes = True
        json_encoders = {
            float: lambda v: round(v, 2) if v is not None else 0.0
        }


class CurrentMonthPerformanceResponse(BaseModel):
    """Current month performance response schema for GET /revenue/current-month"""
    month: int = Field(..., ge=1, le=12, description="Current month number (1-12)")
    month_name: str = Field(..., description="Current month name (e.g., 'January')")
    year: int = Field(..., description="Current year")
    target_amount: float = Field(..., description="Current month's target amount")
    current_revenue: float = Field(..., description="Current month's achieved revenue from all invoices")
    today_revenue: float = Field(..., description="Today's revenue from new invoices issued today")
    performance_percentage: float = Field(..., description="Performance percentage (current_revenue / target_amount * 100)")
    days_remaining: int = Field(..., ge=0, description="Days remaining in the current month")
    previous_month_revenue: float = Field(..., description="Same month from previous year revenue")
    growth_amount: float = Field(..., description="Growth amount compared to same month previous year")
    growth_percentage: float = Field(..., description="Growth percentage compared to same month previous year")
    period: str = Field(..., description="Month period description (e.g., 'January 2025')")

    class Config:
        """Pydantic config"""
        from_attributes = True
        json_encoders = {
            float: lambda v: round(v, 2) if v is not None else 0.0
        }


class CurrentYearPerformanceResponse(BaseModel):
    """Current year performance response schema for GET /revenue/current-year"""
    year: int = Field(..., description="Current year")
    target_amount: float = Field(..., description="Current year's total target amount")
    current_revenue: float = Field(..., description="Year-to-date revenue from all invoices")
    performance_percentage: float = Field(..., description="Performance percentage (current_revenue / target_amount * 100)")
    months_completed: int = Field(..., ge=0, le=12, description="Number of months completed in the year")
    previous_year_revenue: float = Field(..., description="Previous year's total revenue")
    growth_amount: float = Field(..., description="Growth amount compared to previous year")
    growth_percentage: float = Field(..., description="Growth percentage compared to previous year")
    period: str = Field(..., description="Year period description (e.g., '2025')")

    class Config:
        """Pydantic config"""
        from_attributes = True
        json_encoders = {
            float: lambda v: round(v, 2) if v is not None else 0.0
        }