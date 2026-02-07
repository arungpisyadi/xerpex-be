"""
Survey controllers for the XerpeX ERP System
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.survey import (
    Survey as SurveySchema, SurveyCreate, SurveyUpdate, SurveyStatusUpdate,
    SurveyStatus, SurveyPriority, SurveyStats, SalesmanStats
)
from app.services.survey import (
    get_survey, get_surveys, create_survey, update_survey, delete_survey,
    get_surveys_by_salesman, get_overdue_surveys, get_upcoming_visits,
    get_survey_stats, get_salesman_stats
)
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.get("", response_model=List[SurveySchema])
async def read_surveys(
    skip: int = 0,
    limit: int = 999999,
    status: Optional[SurveyStatus] = Query(None, description="Filter by survey status"),
    priority: Optional[SurveyPriority] = Query(None, description="Filter by priority level"),
    salesmen_id: Optional[int] = Query(None, description="Filter by assigned salesman"),
    follow_up_from: Optional[date] = Query(None, description="Start date for follow-up date range"),
    follow_up_to: Optional[date] = Query(None, description="End date for follow-up date range"),
    visiting_from: Optional[date] = Query(None, description="Start date for visiting date range"),
    visiting_to: Optional[date] = Query(None, description="End date for visiting date range"),
    overdue_follow_up: Optional[bool] = Query(None, description="Filter for overdue follow-ups"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all surveys with optional filtering
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by survey status
        priority: Filter by priority level
        salesmen_id: Filter by assigned salesman
        follow_up_from: Start date for follow-up date range
        follow_up_to: End date for follow-up date range
        visiting_from: Start date for visiting date range
        visiting_to: End date for visiting date range
        overdue_follow_up: Filter for overdue follow-ups
        db: Database session
        current_user: Current user
        
    Returns:
        List[Survey]: List of surveys
    """
    # All authenticated users can view surveys
    surveys = get_surveys(
        db, skip=skip, limit=limit, status=status, priority=priority,
        salesmen_id=salesmen_id, follow_up_from=follow_up_from, follow_up_to=follow_up_to,
        visiting_from=visiting_from, visiting_to=visiting_to, overdue_follow_up=overdue_follow_up
    )
    return surveys


@router.post("", response_model=SurveySchema, status_code=status.HTTP_201_CREATED)
async def create_new_survey(
    survey: SurveyCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new survey (email notifications sent in background)
    
    Args:
        survey: Survey data
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current user
        
    Returns:
        Survey: Created survey
    """
    # All authenticated users can create surveys
    return await create_survey(db=db, survey=survey, background_tasks=background_tasks)


@router.get("/overdue", response_model=List[SurveySchema])
async def read_overdue_surveys(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get surveys with overdue follow-up dates
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current user
        
    Returns:
        List[Survey]: List of overdue surveys
    """
    surveys = get_overdue_surveys(db, skip=skip, limit=limit)
    return surveys


@router.get("/upcoming-visits", response_model=List[SurveySchema])
async def read_upcoming_visits(
    days_ahead: int = Query(7, description="Number of days to look ahead"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get surveys with upcoming visiting dates
    
    Args:
        days_ahead: Number of days to look ahead
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current user
        
    Returns:
        List[Survey]: List of surveys with upcoming visits
    """
    surveys = get_upcoming_visits(db, days_ahead=days_ahead, skip=skip, limit=limit)
    return surveys


@router.get("/stats", response_model=SurveyStats)
async def read_survey_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get survey statistics
    
    Args:
        db: Database session
        current_user: Current user
        
    Returns:
        SurveyStats: Survey statistics
    """
    # Only admin and manager can view overall stats
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    stats = get_survey_stats(db)
    return stats


@router.get("/stats/salesman/{salesmen_id}", response_model=SalesmanStats)
async def read_salesman_stats(
    salesmen_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get statistics for a specific salesman
    
    Args:
        salesmen_id: Salesman ID
        db: Database session
        current_user: Current user
        
    Returns:
        SalesmanStats: Salesman statistics
    """
    # Only admin and manager can view salesman stats
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    stats = get_salesman_stats(db, salesmen_id)
    return stats


@router.get("/by-salesman/{salesmen_id}", response_model=List[SurveySchema])
async def read_surveys_by_salesman(
    salesmen_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get surveys by salesman ID
    
    Args:
        salesmen_id: Salesman ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current user
        
    Returns:
        List[Survey]: List of surveys
    """
    surveys = get_surveys_by_salesman(db, salesmen_id, skip=skip, limit=limit)
    return surveys


@router.get("/{survey_id}", response_model=SurveySchema)
async def read_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a survey by ID
    
    Args:
        survey_id: Survey ID
        db: Database session
        current_user: Current user
        
    Returns:
        Survey: Survey
        
    Raises:
        HTTPException: If survey not found
    """
    db_survey = get_survey(db, survey_id=survey_id)
    if db_survey is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    return db_survey


@router.put("/{survey_id}", response_model=SurveySchema)
async def update_survey_endpoint(
    survey_id: int,
    survey_update: SurveyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a survey
    
    Args:
        survey_id: Survey ID
        survey_update: Survey update data
        db: Database session
        current_user: Current user
        
    Returns:
        Survey: Updated survey
        
    Raises:
        HTTPException: If survey not found
    """
    return await update_survey(db=db, survey_id=survey_id, survey_update=survey_update)


@router.put("/{survey_id}/status", response_model=SurveySchema)
async def update_survey_status(
    survey_id: int,
    status_update: SurveyStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update survey status only
    
    Args:
        survey_id: Survey ID
        status_update: Status update data
        db: Database session
        current_user: Current user
        
    Returns:
        Survey: Updated survey
        
    Raises:
        HTTPException: If survey not found
    """
    survey_update = SurveyUpdate(status=status_update.status)
    return await update_survey(db=db, survey_id=survey_id, survey_update=survey_update)


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a survey
    
    Args:
        survey_id: Survey ID
        db: Database session
        current_user: Current user
        
    Raises:
        HTTPException: If survey not found or not enough permissions
    """
    # Only admin can delete surveys
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    delete_survey(db=db, survey_id=survey_id)
    return None