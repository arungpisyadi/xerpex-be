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


class MonthlyData(BaseModel):
    """Monthly data schema"""
    month: int
    month_name: str
    target_amount: float
    achieved_amount: float
    achievement_percentage: float
    carried_over_amount: float


class ChartDataPoint(BaseModel):
    """Chart data point schema"""
    month: int
    month_name: str
    target: float
    achievement: float


class TopPerformer(BaseModel):
    """Top performer schema"""
    user_id: int
    username: str
    full_name: Optional[str] = None
    total_achievement: float
    achievement_percentage: float


class YTDMetrics(BaseModel):
    """Year-to-date metrics schema"""
    ytd_target: float
    ytd_achievement: float
    ytd_percentage: float


class TargetOverview(BaseModel):
    """Enhanced target overview schema for GET /admin/targets/overview"""
    total_yearly_target: float
    current_month_achievement: float
    achievement_percentage: float
    monthly_data: List[MonthlyData] = []
    chart_data: List[ChartDataPoint] = []
    ytd_metrics: YTDMetrics
    active_users_count: int = 0
    top_performers: List[TopPerformer] = []


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


class ChartDataset(BaseModel):
    """Chart dataset schema for bar chart visualization"""
    label: str
    data: List[float]
    backgroundColor: Optional[str] = None
    borderColor: Optional[str] = None


class ChartData(BaseModel):
    """Chart data schema containing labels and datasets"""
    labels: List[str]
    datasets: List[ChartDataset]


class UserPerformanceDetail(BaseModel):
    """Detailed user performance information"""
    user_id: int
    username: str
    full_name: Optional[str]
    target_amount: float
    achieved_amount: float
    achievement_percentage: float
    months_with_data: int


class UserPerformanceChart(BaseModel):
    """User performance chart schema for GET /targets/user-performances"""
    year: int
    chart_data: ChartData
    users: List[UserPerformanceDetail]
    total_users: int
    generated_at: datetime