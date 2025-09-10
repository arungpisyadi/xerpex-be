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


class KPIStatsResponse(BaseModel):
    """KPI statistics response schema"""
    customers: KPIResponse
    bookings: KPIResponse
    surveys: KPIResponse
    quotes: KPIResponse
    
    class Config:
        """Pydantic config"""
        from_attributes = True