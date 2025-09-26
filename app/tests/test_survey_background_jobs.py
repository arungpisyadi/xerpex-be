"""
Tests for survey background jobs functionality
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.survey import Survey
from app.models.survey_job import SurveyJob
from app.models.salesmen import Salesmen
from app.services.survey_background_tasks import (
    create_survey_email_job,
    process_survey_email_notifications,
    get_failed_email_jobs,
    retry_failed_email_jobs,
    cleanup_old_survey_jobs
)
from app.schemas.survey import SurveyCreate, SurveyStatus, SurveyPriority


@pytest.fixture
def sample_survey(db: Session):
    """Create a sample survey for testing"""
    # Create a salesman first
    salesman = Salesmen(
        first_name="Test",
        last_name="Salesman",
        email="salesman@test.com",
        phone_number="+628123456789",
        is_active=True
    )
    db.add(salesman)
    db.commit()
    db.refresh(salesman)
    
    # Create survey
    survey = Survey(
        client_name="Test Client",
        email="client@test.com",
        phone_number="+628987654321",
        estimated_paxes=4,
        villa_types="Villa A",
        notes="Test notes",
        status="new",
        priority="medium",
        salesmen_id=salesman.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    
    return survey


def test_create_survey_email_job(db: Session, sample_survey):
    """Test creating a survey email job"""
    job = create_survey_email_job(db, sample_survey.id)
    
    assert job.survey_id == sample_survey.id
    assert job.status == 'pending'
    assert job.retry_count == 0
    assert job.max_retries == 3
    assert job.message == 'Email job created'
    
    # Verify job is saved to database
    db_job = db.query(SurveyJob).filter(SurveyJob.id == job.id).first()
    assert db_job is not None
    assert db_job.survey_id == sample_survey.id


@pytest.mark.asyncio
async def test_process_survey_email_notifications_success(db: Session, sample_survey):
    """Test successful email notification processing"""
    
    # Mock all email functions to return True
    with patch('app.services.survey_background_tasks.send_survey_notification_to_salesman', new_callable=AsyncMock) as mock_salesman, \
         patch('app.services.survey_background_tasks.send_survey_notification_to_admin', new_callable=AsyncMock) as mock_admin, \
         patch('app.services.survey_background_tasks.send_survey_notification_to_sales_team', new_callable=AsyncMock) as mock_sales_team, \
         patch('app.services.survey_background_tasks.settings') as mock_settings:
        
        # Configure mock settings
        mock_settings.ADMIN_EMAIL = "admin@test.com"
        mock_settings.SALES_ADMIN_EMAIL = "sales.admin@test.com"
        mock_settings.SALES_DIRECTOR_EMAIL = "sales.director@test.com"
        
        # All email functions return True (success)
        mock_salesman.return_value = True
        mock_admin.return_value = True
        mock_sales_team.return_value = True
        
        # Process notifications
        result = await process_survey_email_notifications(sample_survey.id)
        
        # Verify result
        assert result is True
        
        # Verify email functions were called
        mock_salesman.assert_called_once()
        mock_admin.assert_called_once()
        mock_sales_team.assert_called_once()
        
        # Verify job status is updated to success
        job = db.query(SurveyJob).filter(SurveyJob.survey_id == sample_survey.id).first()
        assert job is not None
        assert job.status == 'success'
        assert 'notification sent' in job.message.lower()


@pytest.mark.asyncio
async def test_process_survey_email_notifications_failure(db: Session, sample_survey):
    """Test email notification processing with failures"""
    
    # Mock email functions with failures
    with patch('app.services.survey_background_tasks.send_survey_notification_to_salesman', new_callable=AsyncMock) as mock_salesman, \
         patch('app.services.survey_background_tasks.send_survey_notification_to_admin', new_callable=AsyncMock) as mock_admin, \
         patch('app.services.survey_background_tasks.send_survey_notification_to_sales_team', new_callable=AsyncMock) as mock_sales_team, \
         patch('app.services.survey_background_tasks.settings') as mock_settings:
        
        # Configure mock settings
        mock_settings.ADMIN_EMAIL = "admin@test.com"
        mock_settings.SALES_ADMIN_EMAIL = "sales.admin@test.com"
        mock_settings.SALES_DIRECTOR_EMAIL = "sales.director@test.com"
        
        # Some email functions return False (failure)
        mock_salesman.return_value = False
        mock_admin.return_value = True
        mock_sales_team.return_value = False
        
        # Process notifications
        result = await process_survey_email_notifications(sample_survey.id)
        
        # Verify result is False due to failures
        assert result is False
        
        # Verify job status is updated to failed
        job = db.query(SurveyJob).filter(SurveyJob.survey_id == sample_survey.id).first()
        assert job is not None
        assert job.status == 'failed'
        assert job.retry_count == 1
        assert job.next_retry_at is not None
        assert 'failed' in job.message.lower()


def test_get_failed_email_jobs(db: Session, sample_survey):
    """Test getting failed email jobs ready for retry"""
    # Create a failed job ready for retry
    now = datetime.utcnow()
    past_time = now - timedelta(minutes=15)
    
    job1 = SurveyJob(
        survey_id=sample_survey.id,
        status='failed',
        retry_count=1,
        max_retries=3,
        next_retry_at=past_time,  # Ready for retry
        created_at=now,
        updated_at=now
    )
    
    # Create a failed job not ready for retry
    future_time = now + timedelta(minutes=15)
    job2 = SurveyJob(
        survey_id=sample_survey.id,
        status='failed',
        retry_count=2,
        max_retries=3,
        next_retry_at=future_time,  # Not ready for retry
        created_at=now,
        updated_at=now
    )
    
    # Create a failed job that exceeded max retries
    job3 = SurveyJob(
        survey_id=sample_survey.id,
        status='failed',
        retry_count=3,
        max_retries=3,  # Exceeded max retries
        next_retry_at=past_time,
        created_at=now,
        updated_at=now
    )
    
    # Create a successful job
    job4 = SurveyJob(
        survey_id=sample_survey.id,
        status='success',
        retry_count=0,
        max_retries=3,
        created_at=now,
        updated_at=now
    )
    
    db.add_all([job1, job2, job3, job4])
    db.commit()
    
    # Get failed jobs ready for retry
    failed_jobs = get_failed_email_jobs(db, limit=10)
    
    # Only job1 should be returned
    assert len(failed_jobs) == 1
    assert failed_jobs[0].id == job1.id


@pytest.mark.asyncio
async def test_retry_failed_email_jobs(db: Session, sample_survey):
    """Test retrying failed email jobs"""
    # Create a failed job
    now = datetime.utcnow()
    past_time = now - timedelta(minutes=15)
    
    job = SurveyJob(
        survey_id=sample_survey.id,
        status='failed',
        retry_count=1,
        max_retries=3,
        next_retry_at=past_time,
        created_at=now,
        updated_at=now
    )
    db.add(job)
    db.commit()
    
    # Mock the process_survey_email_notifications function
    with patch('app.services.survey_background_tasks.process_survey_email_notifications', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = True
        
        # Retry failed jobs
        processed_count = await retry_failed_email_jobs(limit=10)
        
        # Verify one job was processed
        assert processed_count == 1
        mock_process.assert_called_once_with(sample_survey.id)


@pytest.mark.asyncio
async def test_cleanup_old_survey_jobs(db: Session, sample_survey):
    """Test cleaning up old survey jobs"""
    now = datetime.utcnow()
    old_date = now - timedelta(days=35)  # Older than 30 days
    recent_date = now - timedelta(days=15)  # Within 30 days
    
    # Create old successful job (should be deleted)
    job1 = SurveyJob(
        survey_id=sample_survey.id,
        status='success',
        retry_count=0,
        max_retries=3,
        created_at=old_date,
        updated_at=old_date
    )
    
    # Create old failed job with max retries exceeded (should be deleted)
    job2 = SurveyJob(
        survey_id=sample_survey.id,
        status='failed',
        retry_count=3,
        max_retries=3,
        created_at=old_date,
        updated_at=old_date
    )
    
    # Create recent successful job (should not be deleted)
    job3 = SurveyJob(
        survey_id=sample_survey.id,
        status='success',
        retry_count=0,
        max_retries=3,
        created_at=recent_date,
        updated_at=recent_date
    )
    
    # Create old failed job with retries remaining (should not be deleted)
    job4 = SurveyJob(
        survey_id=sample_survey.id,
        status='failed',
        retry_count=1,
        max_retries=3,
        created_at=old_date,
        updated_at=old_date
    )
    
    db.add_all([job1, job2, job3, job4])
    db.commit()
    
    # Run cleanup
    await cleanup_old_survey_jobs(days_old=30)
    
    # Check which jobs remain
    remaining_jobs = db.query(SurveyJob).all()
    remaining_ids = [job.id for job in remaining_jobs]
    
    # Only job3 and job4 should remain
    assert len(remaining_jobs) == 2
    assert job3.id in remaining_ids
    assert job4.id in remaining_ids
    assert job1.id not in remaining_ids
    assert job2.id not in remaining_ids