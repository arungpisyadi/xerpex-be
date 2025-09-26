"""
Background tasks for Survey email notifications
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.database import SessionLocal
from app.models.survey import Survey
from app.models.survey_job import SurveyJob
from app.services.email import (
    send_survey_notification_to_salesman,
    send_survey_notification_to_admin,
    send_survey_notification_to_sales_team
)
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)


def create_survey_email_job(db: Session, survey_id: int) -> SurveyJob:
    """
    Create a new survey email job
    
    Args:
        db: Database session
        survey_id: Survey ID
        
    Returns:
        SurveyJob: Created survey job
    """
    survey_job = SurveyJob(
        survey_id=survey_id,
        status='pending',
        message='Email job created',
        retry_count=0,
        max_retries=3,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(survey_job)
    db.commit()
    db.refresh(survey_job)
    
    logger.info(f"Created email job for survey {survey_id}")
    return survey_job


async def process_survey_email_notifications(survey_id: int) -> bool:
    """
    Process email notifications for a survey
    
    Args:
        survey_id: Survey ID
        
    Returns:
        bool: True if all emails sent successfully
    """
    db = SessionLocal()
    try:
        # Get survey with related data
        survey = db.query(Survey).options(joinedload(Survey.salesman)).filter(Survey.id == survey_id).first()
        if not survey:
            logger.error(f"Survey {survey_id} not found")
            return False

        # Get or create survey job
        survey_job = db.query(SurveyJob).filter(SurveyJob.survey_id == survey_id).first()
        if not survey_job:
            survey_job = create_survey_email_job(db, survey_id)
        
        # Update job status to processing
        survey_job.status = 'processing'
        survey_job.updated_at = datetime.utcnow()
        db.commit()
        
        # Prepare survey data for email
        survey_data = {
            'client_name': survey.client_name,
            'email': survey.email if survey.email else 'N/A',
            'phone_number': survey.phone_number,
            'estimated_paxes': survey.estimated_paxes,
            'villa_types': survey.villa_types,
            'notes': survey.notes,
            'status': survey.status,
            'priority': survey.priority,
            'follow_up_date': str(survey.follow_up_date) if survey.follow_up_date else None,
            'visiting_date': str(survey.visiting_date) if survey.visiting_date else None,
        }
        
        success_messages = []
        error_messages = []
        
        # Send to salesman if not default (ID != 1) and salesman exists
        if survey.salesmen_id != 1 and survey.salesman:
            try:
                success = await send_survey_notification_to_salesman(
                    salesman_email=survey.salesman.email,
                    salesman_name=survey.salesman.full_name,
                    survey_data=survey_data
                )
                if success:
                    success_messages.append(f"Salesman notification sent to {survey.salesman.email}")
                else:
                    error_messages.append(f"Failed to send salesman notification to {survey.salesman.email}")
            except Exception as e:
                error_messages.append(f"Exception sending to salesman {survey.salesman.email}: {str(e)}")
        
        # Send to admin if configured
        if settings.ADMIN_EMAIL:
            try:
                success = await send_survey_notification_to_admin(
                    admin_email=settings.ADMIN_EMAIL,
                    survey_data=survey_data,
                    salesman_name=survey.salesman.full_name if survey.salesman else "Default Salesman"
                )
                if success:
                    success_messages.append(f"Admin notification sent to {settings.ADMIN_EMAIL}")
                else:
                    error_messages.append(f"Failed to send admin notification to {settings.ADMIN_EMAIL}")
            except Exception as e:
                error_messages.append(f"Exception sending to admin {settings.ADMIN_EMAIL}: {str(e)}")
        
        # Send to sales team if configured
        try:
            success = await send_survey_notification_to_sales_team(
                sales_admin_email=settings.SALES_ADMIN_EMAIL,
                sales_director_email=settings.SALES_DIRECTOR_EMAIL,
                survey_data=survey_data,
                salesman_name=survey.salesman.full_name if survey.salesman else "Default Salesman"
            )
            if success:
                recipients = []
                if settings.SALES_ADMIN_EMAIL:
                    recipients.append(settings.SALES_ADMIN_EMAIL)
                if settings.SALES_DIRECTOR_EMAIL:
                    recipients.append(settings.SALES_DIRECTOR_EMAIL)
                success_messages.append(f"Sales team notification sent to {', '.join(recipients)}")
            else:
                recipients = []
                if settings.SALES_ADMIN_EMAIL:
                    recipients.append(settings.SALES_ADMIN_EMAIL)
                if settings.SALES_DIRECTOR_EMAIL:
                    recipients.append(settings.SALES_DIRECTOR_EMAIL)
                error_messages.append(f"Failed to send sales team notification to {', '.join(recipients)}")
        except Exception as e:
            error_messages.append(f"Exception sending to sales team: {str(e)}")
        
        # Update job status based on results
        all_messages = success_messages + error_messages
        survey_job.message = '; '.join(all_messages) if all_messages else 'No notifications to send'
        survey_job.updated_at = datetime.utcnow()
        
        if error_messages:
            survey_job.status = 'failed'
            survey_job.retry_count += 1
            # Schedule retry in 10 minutes
            survey_job.next_retry_at = datetime.utcnow() + timedelta(minutes=10)
            logger.error(f"Email job {survey_job.id} failed: {'; '.join(error_messages)}")
        else:
            survey_job.status = 'success'
            survey_job.next_retry_at = None
            logger.info(f"Email job {survey_job.id} completed successfully")
        
        db.commit()
        return len(error_messages) == 0
        
    except Exception as e:
        logger.error(f"Failed to process email notifications for survey {survey_id}: {str(e)}")
        # Update job status to failed
        if 'survey_job' in locals():
            survey_job.status = 'failed'
            survey_job.message = f"Exception: {str(e)}"
            survey_job.retry_count += 1
            survey_job.next_retry_at = datetime.utcnow() + timedelta(minutes=10)
            survey_job.updated_at = datetime.utcnow()
            db.commit()
        return False
    finally:
        db.close()


def get_failed_email_jobs(db: Session, limit: int = 50) -> List[SurveyJob]:
    """
    Get failed email jobs that are ready for retry
    
    Args:
        db: Database session
        limit: Maximum number of jobs to return
        
    Returns:
        List[SurveyJob]: List of failed jobs ready for retry
    """
    now = datetime.utcnow()
    
    failed_jobs = db.query(SurveyJob).filter(
        and_(
            SurveyJob.status == 'failed',
            SurveyJob.retry_count < SurveyJob.max_retries,
            or_(
                SurveyJob.next_retry_at.is_(None),
                SurveyJob.next_retry_at <= now
            )
        )
    ).limit(limit).all()
    
    return failed_jobs


async def retry_failed_email_jobs(limit: int = 50) -> int:
    """
    Retry failed email jobs
    
    Args:
        limit: Maximum number of jobs to retry
        
    Returns:
        int: Number of jobs processed
    """
    db = SessionLocal()
    processed_count = 0
    
    try:
        failed_jobs = get_failed_email_jobs(db, limit)
        
        for job in failed_jobs:
            logger.info(f"Retrying email job {job.id} for survey {job.survey_id} (attempt {job.retry_count + 1})")
            
            # Process the email notifications
            success = await process_survey_email_notifications(job.survey_id)
            processed_count += 1
            
            if not success:
                logger.warning(f"Retry failed for email job {job.id}")
        
        logger.info(f"Processed {processed_count} failed email jobs")
        
    except Exception as e:
        logger.error(f"Error retrying failed email jobs: {str(e)}")
    finally:
        db.close()
    
    return processed_count


async def cleanup_old_survey_jobs(days_old: int = 30):
    """
    Clean up old completed survey jobs
    
    Args:
        days_old: Number of days old jobs to keep
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Delete old successful jobs
        deleted_count = db.query(SurveyJob).filter(
            and_(
                SurveyJob.status == 'success',
                SurveyJob.updated_at < cutoff_date
            )
        ).delete()
        
        # Delete old failed jobs that exceeded max retries
        deleted_count += db.query(SurveyJob).filter(
            and_(
                SurveyJob.status == 'failed',
                SurveyJob.retry_count >= SurveyJob.max_retries,
                SurveyJob.updated_at < cutoff_date
            )
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted_count} old survey jobs")
        
    except Exception as e:
        logger.error(f"Error cleaning up old survey jobs: {str(e)}")
        db.rollback()
    finally:
        db.close()