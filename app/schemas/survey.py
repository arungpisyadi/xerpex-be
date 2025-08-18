"""
Survey schemas for the XerpeX ERP System
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from enum import Enum

from app.schemas.salesmen import SalesmenSummary


class SurveyStatus(str, Enum):
    """Survey status enum"""
    NEW = "new"
    CONTACTED = "contacted"
    SCHEDULED = "scheduled"
    VISITED = "visited"
    QUOTED = "quoted"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class SurveyPriority(str, Enum):
    """Survey priority enum"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SurveyBase(BaseModel):
    """Base survey schema"""
    client_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    estimated_paxes: int
    villa_types: Optional[str] = None
    notes: Optional[str] = None
    status: SurveyStatus = SurveyStatus.NEW
    priority: SurveyPriority = SurveyPriority.MEDIUM
    follow_up_date: Optional[date] = None
    visiting_date: Optional[date] = None
    salesmen_id: Optional[int] = 1


class SurveyCreate(SurveyBase):
    """Survey creation schema"""
    pass


class SurveyUpdate(BaseModel):
    """Survey update schema"""
    client_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    estimated_paxes: Optional[int] = None
    villa_types: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[SurveyStatus] = None
    priority: Optional[SurveyPriority] = None
    follow_up_date: Optional[date] = None
    visiting_date: Optional[date] = None
    salesmen_id: Optional[int] = None


class SurveyStatusUpdate(BaseModel):
    """Survey status update schema"""
    status: SurveyStatus


class SurveyInDB(SurveyBase):
    """Survey in database schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class Survey(SurveyInDB):
    """Survey schema"""
    salesman: Optional[SalesmenSummary] = None

    class Config:
        """Pydantic config"""
        from_attributes = True


class SurveyWithSalesman(Survey):
    """Survey with salesman details schema"""
    pass


class SurveyStats(BaseModel):
    """Survey statistics schema"""
    total_surveys: int
    by_status: dict
    by_priority: dict
    conversion_rate: float
    avg_days_to_close: Optional[float] = None


class SalesmanStats(BaseModel):
    """Salesman statistics schema"""
    salesman_id: int
    salesman_name: str
    total_surveys: int
    by_status: dict
    conversion_rate: float
    avg_days_to_close: Optional[float] = None