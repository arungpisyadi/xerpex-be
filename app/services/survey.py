"""
Survey services for the XerpeX ERP System
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.models.survey import Survey
from app.models.salesmen import Salesmen
from app.schemas.survey import SurveyCreate, SurveyUpdate, SurveyStatus, SurveyPriority
from app.services.email import (
    send_survey_notification_to_salesman,
    send_survey_notification_to_admin,
    send_survey_status_update_notification,
    send_survey_notification_to_sales_team
)
from app.config import settings
def get_survey(db: Session, survey_id: int) -> Optional[Survey]:
    """
    Get a survey by ID with salesman details
    
    Args:
        db: Database session
        survey_id: Survey ID
        
    Returns:
        Survey: Survey or None
    """
    return db.query(Survey).options(joinedload(Survey.salesman)).filter(Survey.id == survey_id).first()


def get_surveys(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[SurveyStatus] = None,
    priority: Optional[SurveyPriority] = None,
    salesmen_id: Optional[int] = None,
    follow_up_from: Optional[date] = None,
    follow_up_to: Optional[date] = None,
    visiting_from: Optional[date] = None,
    visiting_to: Optional[date] = None,
    overdue_follow_up: Optional[bool] = None
) -> List[Survey]:
    """
    Get surveys with optional filtering
    
    Args:
        db: Database session
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
        
    Returns:
        List[Survey]: List of surveys
    """
    query = db.query(Survey).options(joinedload(Survey.salesman))
    
    if status:
        query = query.filter(Survey.status == status.value)
    
    if priority:
        query = query.filter(Survey.priority == priority.value)
    
    if salesmen_id:
        query = query.filter(Survey.salesmen_id == salesmen_id)
    
    if follow_up_from:
        query = query.filter(Survey.follow_up_date >= follow_up_from)
    
    if follow_up_to:
        query = query.filter(Survey.follow_up_date <= follow_up_to)
    
    if visiting_from:
        query = query.filter(Survey.visiting_date >= visiting_from)
    
    if visiting_to:
        query = query.filter(Survey.visiting_date <= visiting_to)
    
    if overdue_follow_up:
        today = date.today()
        query = query.filter(
            and_(
                Survey.follow_up_date.isnot(None),
                Survey.follow_up_date < today,
                Survey.status.notin_(['closed_won', 'closed_lost'])
            )
        )
    
    return query.order_by(Survey.created_at.desc()).offset(skip).limit(limit).all()


async def create_survey(db: Session, survey: SurveyCreate) -> Survey:
    """
    Create a new survey and send notifications
    
    Args:
        db: Database session
        survey: Survey data
        
    Returns:
        Survey: Created survey
    """
    # Create new survey
    db_survey = Survey(
        client_name=survey.client_name,
        email=survey.email,
        phone_number=survey.phone_number,
        estimated_paxes=survey.estimated_paxes,
        villa_types=survey.villa_types,
        notes=survey.notes,
        status=survey.status.value,
        priority=survey.priority.value,
        follow_up_date=survey.follow_up_date,
        visiting_date=survey.visiting_date,
        salesmen_id=survey.salesmen_id or 1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_survey)
    db.commit()
    db.refresh(db_survey)
    
    # Load salesman details for notifications
    db_survey = get_survey(db, db_survey.id)
    
    # Prepare survey data for email
    survey_data = {
        'client_name': db_survey.client_name,
        'email': db_survey.email if db_survey.email else 'N/A',
        'phone_number': db_survey.phone_number,
        'estimated_paxes': db_survey.estimated_paxes,
        'villa_types': db_survey.villa_types,
        'notes': db_survey.notes,
        'status': db_survey.status,
        'priority': db_survey.priority,
        'follow_up_date': str(db_survey.follow_up_date) if db_survey.follow_up_date else None,
        'visiting_date': str(db_survey.visiting_date) if db_survey.visiting_date else None,
    }
    
    # Send notifications
    try:
        # Send to salesman if not default (ID != 1) and salesman exists
        if db_survey.salesmen_id != 1 and db_survey.salesman:
            await send_survey_notification_to_salesman(
                salesman_email=db_survey.salesman.email,
                salesman_name=db_survey.salesman.full_name,
                survey_data=survey_data
            )
        
        # Send to admin if configured
        if settings.ADMIN_EMAIL:
            await send_survey_notification_to_admin(
                admin_email=settings.ADMIN_EMAIL,
                survey_data=survey_data,
                salesman_name=db_survey.salesman.full_name if db_survey.salesman else "Default Salesman"
            )
        
        # Send to sales team (admin and director) if configured
        await send_survey_notification_to_sales_team(
            sales_admin_email=settings.SALES_ADMIN_EMAIL,
            sales_director_email=settings.SALES_DIRECTOR_EMAIL,
            survey_data=survey_data,
            salesman_name=db_survey.salesman.full_name if db_survey.salesman else "Default Salesman"
        )
    except Exception as e:
        # Log error but don't fail the survey creation
        print(f"Failed to send email notifications: {str(e)}")
    
    return db_survey


async def update_survey(db: Session, survey_id: int, survey_update: SurveyUpdate) -> Survey:
    """
    Update a survey
    
    Args:
        db: Database session
        survey_id: Survey ID
        survey_update: Survey update data
        
    Returns:
        Survey: Updated survey
        
    Raises:
        HTTPException: If survey not found
    """
    db_survey = get_survey(db, survey_id)
    if not db_survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Store old status for notification
    old_status = db_survey.status
    
    # Update survey fields
    update_data = survey_update.dict(exclude_unset=True)
    
    # Convert enum values to strings
    if 'status' in update_data and update_data['status']:
        update_data['status'] = update_data['status'].value
    if 'priority' in update_data and update_data['priority']:
        update_data['priority'] = update_data['priority'].value
    
    for key, value in update_data.items():
        setattr(db_survey, key, value)
    
    db_survey.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_survey)
    
    # Send status change notification if status changed
    if 'status' in update_data and old_status != db_survey.status:
        try:
            survey_data = {
                'client_name': db_survey.client_name,
                'email': db_survey.email if db_survey.email else 'N/A',
                'priority': db_survey.priority,
                'follow_up_date': str(db_survey.follow_up_date) if db_survey.follow_up_date else None,
                'visiting_date': str(db_survey.visiting_date) if db_survey.visiting_date else None,
            }
            
            # Notify salesman if not default
            if db_survey.salesmen_id != 1 and db_survey.salesman:
                await send_survey_status_update_notification(
                    recipient_email=db_survey.salesman.email,
                    recipient_name=db_survey.salesman.full_name,
                    survey_data=survey_data,
                    old_status=old_status,
                    new_status=db_survey.status
                )
            
            # Notify admin if configured
            if settings.ADMIN_EMAIL:
                await send_survey_status_update_notification(
                    recipient_email=settings.ADMIN_EMAIL,
                    recipient_name="Admin",
                    survey_data=survey_data,
                    old_status=old_status,
                    new_status=db_survey.status
                )
        except Exception as e:
            print(f"Failed to send status update notifications: {str(e)}")
    
    return get_survey(db, survey_id)


def delete_survey(db: Session, survey_id: int) -> bool:
    """
    Delete a survey
    
    Args:
        db: Database session
        survey_id: Survey ID
        
    Returns:
        bool: True if survey was deleted
        
    Raises:
        HTTPException: If survey not found
    """
    db_survey = get_survey(db, survey_id)
    if not db_survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    db.delete(db_survey)
    db.commit()
    
    return True


def get_surveys_by_salesman(db: Session, salesmen_id: int, skip: int = 0, limit: int = 100) -> List[Survey]:
    """
    Get surveys by salesman ID
    
    Args:
        db: Database session
        salesmen_id: Salesman ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[Survey]: List of surveys
    """
    return db.query(Survey).options(joinedload(Survey.salesman)).filter(
        Survey.salesmen_id == salesmen_id
    ).order_by(Survey.created_at.desc()).offset(skip).limit(limit).all()


def get_overdue_surveys(db: Session, skip: int = 0, limit: int = 100) -> List[Survey]:
    """
    Get surveys with overdue follow-up dates
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[Survey]: List of overdue surveys
    """
    today = date.today()
    return db.query(Survey).options(joinedload(Survey.salesman)).filter(
        and_(
            Survey.follow_up_date.isnot(None),
            Survey.follow_up_date < today,
            Survey.status.notin_(['closed_won', 'closed_lost'])
        )
    ).order_by(Survey.follow_up_date.asc()).offset(skip).limit(limit).all()


def get_upcoming_visits(db: Session, days_ahead: int = 7, skip: int = 0, limit: int = 100) -> List[Survey]:
    """
    Get surveys with upcoming visiting dates
    
    Args:
        db: Database session
        days_ahead: Number of days to look ahead
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[Survey]: List of surveys with upcoming visits
    """
    today = date.today()
    future_date = date.today().replace(day=today.day + days_ahead) if today.day + days_ahead <= 31 else date.today().replace(month=today.month + 1, day=(today.day + days_ahead) % 31)
    
    return db.query(Survey).options(joinedload(Survey.salesman)).filter(
        and_(
            Survey.visiting_date.isnot(None),
            Survey.visiting_date >= today,
            Survey.visiting_date <= future_date
        )
    ).order_by(Survey.visiting_date.asc()).offset(skip).limit(limit).all()


def get_survey_stats(db: Session) -> Dict[str, Any]:
    """
    Get survey statistics
    
    Args:
        db: Database session
        
    Returns:
        Dict: Survey statistics
    """
    total_surveys = db.query(Survey).count()
    
    # Status distribution
    status_stats = db.query(
        Survey.status,
        func.count(Survey.id).label('count')
    ).group_by(Survey.status).all()
    
    status_dict = {stat.status: stat.count for stat in status_stats}
    
    # Priority distribution
    priority_stats = db.query(
        Survey.priority,
        func.count(Survey.id).label('count')
    ).group_by(Survey.priority).all()
    
    priority_dict = {stat.priority: stat.count for stat in priority_stats}
    
    # Conversion rate
    closed_won = status_dict.get('closed_won', 0)
    closed_lost = status_dict.get('closed_lost', 0)
    total_closed = closed_won + closed_lost
    conversion_rate = (closed_won / total_closed * 100) if total_closed > 0 else 0
    
    return {
        'total_surveys': total_surveys,
        'by_status': status_dict,
        'by_priority': priority_dict,
        'conversion_rate': round(conversion_rate, 2)
    }


def get_salesman_stats(db: Session, salesmen_id: int) -> Dict[str, Any]:
    """
    Get statistics for a specific salesman
    
    Args:
        db: Database session
        salesmen_id: Salesman ID
        
    Returns:
        Dict: Salesman statistics
    """
    # Get salesman info
    salesman = db.query(Salesmen).filter(Salesmen.id == salesmen_id).first()
    if not salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )
    
    total_surveys = db.query(Survey).filter(Survey.salesmen_id == salesmen_id).count()
    
    # Status distribution
    status_stats = db.query(
        Survey.status,
        func.count(Survey.id).label('count')
    ).filter(Survey.salesmen_id == salesmen_id).group_by(Survey.status).all()
    
    status_dict = {stat.status: stat.count for stat in status_stats}
    
    # Conversion rate
    closed_won = status_dict.get('closed_won', 0)
    closed_lost = status_dict.get('closed_lost', 0)
    total_closed = closed_won + closed_lost
    conversion_rate = (closed_won / total_closed * 100) if total_closed > 0 else 0
    
    return {
        'salesman_id': salesmen_id,
        'salesman_name': salesman.full_name,
        'total_surveys': total_surveys,
        'by_status': status_dict,
        'conversion_rate': round(conversion_rate, 2)
    }