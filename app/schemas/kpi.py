"""
KPI schemas for the XerpeX ERP System
"""
from pydantic import BaseModel, Field
from typing import Optional


class KPIResponse(BaseModel):
    """KPI response schema for API responses"""
    total: int = Field(..., description="Total count for the current month")
    growth_percentage: float = Field(..., description="Growth percentage compared to previous month")
    previous_month_total: int = Field(..., description="Total count for the previous month")
    period: str = Field(..., description="Period description (e.g., 'January 2025')")
    
    class Config:
        """Pydantic config"""
        from_attributes = True
        json_encoders = {
            float: lambda v: round(v, 2) if v is not None else 0.0
        }


class SalesPersonPerformance(BaseModel):
    """Individual sales person performance schema"""
    sales_person_id: int = Field(..., description="Sales person user ID")
    sales_person_name: str = Field(..., description="Full name of the sales person")
    revenues: float = Field(..., description="Total revenue from invoices for the current month")
    target: float = Field(default=0.0, description="Sales target for the current month")
    
    class Config:
        """Pydantic config"""
        from_attributes = True
        json_encoders = {
            float: lambda v: round(v, 2) if v is not None else 0.0
        }


class MonthlyRevenuePerSalesResponse(BaseModel):
    """Monthly revenue per sales person response schema"""
    month: str = Field(..., description="Month name (e.g., 'January')")
    year: str = Field(..., description="Year (e.g., '2026')")
    sales_performance: list = Field(..., description="List of sales person performance data")
    
    class Config:
        """Pydantic config"""
        from_attributes = True
        json_encoders = {
            float: lambda v: round(v, 2) if v is not None else 0.0
        }


class KPIStatsResponse(BaseModel):
    """KPI statistics response schema"""
    customers: KPIResponse
    bookings: KPIResponse
    surveys: KPIResponse
    quotes: KPIResponse
    
    class Config:
        """Pydantic config"""
        from_attributes = True