"""
Target schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class TargetBase(BaseModel):
    """Base target schema"""
    user_id: int
    year: int
    month: int
    target_amount: float


class TargetCreate(TargetBase):
    """Target creation schema for POST /admin/targets"""
    pass


class TargetUpdate(BaseModel):
    """Target update schema"""
    target_amount: Optional[float] = None


class TargetInDB(TargetBase):
    """Target in database schema"""
    id: int
    carried_over_amount: float
    adjusted_target_amount: float
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class TargetResponse(TargetInDB):
    """Target response schema"""
    pass


class TargetOverview(BaseModel):
    """Target overview schema for GET /targets/overview"""
    total_yearly_target: float
    current_month_achievement: float
    achievement_percentage: float
    monthly_data: List[Dict[str, Any]]
    chart_data: List[Dict[str, Any]]


class MyPerformance(BaseModel):
    """My performance schema for GET /targets/my-performance"""
    user_id: int
    year: int
    monthly_targets: List[Dict[str, Any]]
    monthly_achievements: List[Dict[str, Any]]
    total_achievement: float
    achievement_percentage: float


class CompanyPerformance(BaseModel):
    """Company performance schema for GET /targets/company-performance"""
    year: int
    total_yearly_target: float
    total_achievement: float
    achievement_percentage: float
    user_performances: List[Dict[str, Any]]