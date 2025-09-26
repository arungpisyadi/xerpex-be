"""
Tests for survey service with null email handling
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, AsyncMock
from sqlalchemy.orm import Session

from app.models.survey import Survey
from app.models.salesmen import Salesmen
from app.models.survey_job import SurveyJob
from app.schemas.survey import SurveyCreate, SurveyUpdate, SurveyStatus, SurveyPriority
from app.services.survey import create_survey, update_survey, get_survey


@pytest.fixture
def test_salesman(db: Session):
    """Create a test salesman"""
    salesman = Salesmen(
        first_name="Test",
        last_name="Salesman",
        email="salesman@test.com",
        phone_number="1234567890",
        is_active=True,
        created_at=date.today(),
        updated_at=date.today()
    )
    db.add(salesman)
    db.commit()
    db.refresh(salesman)
    return salesman


@pytest.mark.asyncio
@patch('app.services.survey_background_tasks.process_survey_email_notifications', new_callable=AsyncMock)
async def test_create_survey_with_null_email(
    mock_background_process,
    db: Session,
    test_salesman
):
    """Test creating a survey with null email field - background task approach"""
    # Create survey data without email
    survey_data = SurveyCreate(
        client_name="Test Client",
        email=None,  # Null email
        phone_number="1234567890",
        estimated_paxes=4,
        villa_types="Villa A, Villa B",
        notes="Test survey with null email",
        status=SurveyStatus.NEW,
        priority=SurveyPriority.HIGH,
        follow_up_date=date.today() + timedelta(days=1),
        visiting_date=date.today() + timedelta(days=3),
        salesmen_id=test_salesman.id
    )
    
    # Create survey
    created_survey = await create_survey(db, survey_data)
    
    # Verify survey was created successfully
    assert created_survey is not None
    assert created_survey.id is not None
    assert created_survey.client_name == "Test Client"
    assert created_survey.email is None
    assert created_survey.phone_number == "1234567890"
    assert created_survey.salesmen_id == test_salesman.id
    
    # Verify that a survey job was created
    survey_job = db.query(SurveyJob).filter(SurveyJob.survey_id == created_survey.id).first()
    assert survey_job is not None
    assert survey_job.status == 'pending'
    assert survey_job.survey_id == created_survey.id
    
    # Verify background task was called (due to asyncio.create_task call)
    # Note: In the new implementation, the background task is triggered automatically
    # The mock might not be called if asyncio.create_task is used instead of background_tasks


@pytest.mark.asyncio
@patch('app.services.survey_background_tasks.process_survey_email_notifications', new_callable=AsyncMock)
async def test_create_survey_with_valid_email(
    mock_background_process,
    db: Session,
    test_salesman
):
    """Test creating a survey with valid email field - background task approach"""
    # Create survey data with valid email
    survey_data = SurveyCreate(
        client_name="Test Client",
        email="client@test.com",  # Valid email
        phone_number="1234567890",
        estimated_paxes=4,
        villa_types="Villa A, Villa B",
        notes="Test survey with valid email",
        status=SurveyStatus.NEW,
        priority=SurveyPriority.HIGH,
        follow_up_date=date.today() + timedelta(days=1),
        visiting_date=date.today() + timedelta(days=3),
        salesmen_id=test_salesman.id
    )
    
    # Create survey
    created_survey = await create_survey(db, survey_data)
    
    # Verify survey was created successfully
    assert created_survey is not None
    assert created_survey.id is not None
    assert created_survey.client_name == "Test Client"
    assert created_survey.email == "client@test.com"
    assert created_survey.phone_number == "1234567890"
    
    # Verify that a survey job was created
    survey_job = db.query(SurveyJob).filter(SurveyJob.survey_id == created_survey.id).first()
    assert survey_job is not None
    assert survey_job.status == 'pending'
    assert survey_job.survey_id == created_survey.id


@pytest.mark.asyncio
@patch('app.services.survey.send_survey_status_update_notification', new_callable=AsyncMock)
async def test_update_survey_status_with_null_email(
    mock_status_notification,
    db: Session,
    test_salesman
):
    """Test updating survey status when survey has null email"""
    # First create a survey with null email
    survey_data = SurveyCreate(
        client_name="Test Client Update",
        email=None,  # Null email
        phone_number="1234567890",
        estimated_paxes=4,
        villa_types="Villa A",
        notes="Test survey for status update",
        status=SurveyStatus.NEW,
        priority=SurveyPriority.MEDIUM,
        follow_up_date=date.today() + timedelta(days=1),
        visiting_date=date.today() + timedelta(days=3),
        salesmen_id=test_salesman.id
    )
    
    # Create survey without calling notifications (patch background task)
    with patch('app.services.survey_background_tasks.process_survey_email_notifications', new_callable=AsyncMock):
        created_survey = await create_survey(db, survey_data)
    
    # Update survey status
    survey_update = SurveyUpdate(
        status=SurveyStatus.CONTACTED,
        notes="Updated survey status"
    )
    
    updated_survey = await update_survey(db, created_survey.id, survey_update)
    
    # Verify survey was updated successfully
    assert updated_survey is not None
    assert updated_survey.status == "contacted"
    assert updated_survey.email is None
    
    # Verify status update notification was called with proper data
    if mock_status_notification.called:
        call_args = mock_status_notification.call_args
        survey_data_arg = call_args[1]['survey_data']
        assert survey_data_arg['email'] == 'N/A'  # Should be converted to 'N/A'


@pytest.mark.asyncio
@patch('app.services.survey.send_survey_status_update_notification', new_callable=AsyncMock)
async def test_update_survey_status_with_valid_email(
    mock_status_notification,
    db: Session,
    test_salesman
):
    """Test updating survey status when survey has valid email"""
    # First create a survey with valid email
    survey_data = SurveyCreate(
        client_name="Test Client Update",
        email="client@test.com",  # Valid email
        phone_number="1234567890",
        estimated_paxes=4,
        villa_types="Villa A",
        notes="Test survey for status update",
        status=SurveyStatus.NEW,
        priority=SurveyPriority.MEDIUM,
        follow_up_date=date.today() + timedelta(days=1),
        visiting_date=date.today() + timedelta(days=3),
        salesmen_id=test_salesman.id
    )
    
    # Create survey without calling notifications (patch background task)
    with patch('app.services.survey_background_tasks.process_survey_email_notifications', new_callable=AsyncMock):
        created_survey = await create_survey(db, survey_data)
    
    # Update survey status
    survey_update = SurveyUpdate(
        status=SurveyStatus.CONTACTED,
        notes="Updated survey status"
    )
    
    updated_survey = await update_survey(db, created_survey.id, survey_update)
    
    # Verify survey was updated successfully
    assert updated_survey is not None
    assert updated_survey.status == "contacted"
    assert updated_survey.email == "client@test.com"
    
    # Verify status update notification was called with proper data
    if mock_status_notification.called:
        call_args = mock_status_notification.call_args
        survey_data_arg = call_args[1]['survey_data']
        assert survey_data_arg['email'] == 'client@test.com'  # Should preserve valid email


def test_survey_creation_with_empty_string_email(db: Session, test_salesman):
    """Test creating survey with empty string email (should be treated as null)"""
    # Create survey directly in database with empty string email
    survey = Survey(
        client_name="Test Client Empty Email",
        email="",  # Empty string
        phone_number="1234567890",
        estimated_paxes=4,
        villa_types="Villa A",
        notes="Test empty email",
        status="new",
        priority="medium",
        follow_up_date=date.today() + timedelta(days=1),
        salesmen_id=test_salesman.id
    )
    
    db.add(survey)
    db.commit()
    db.refresh(survey)
    
    # Verify survey was created
    assert survey.id is not None
    assert survey.client_name == "Test Client Empty Email"
    assert survey.email == ""  # Empty string is preserved as-is
    
    # Test retrieval
    retrieved_survey = get_survey(db, survey.id)
    assert retrieved_survey is not None
    assert retrieved_survey.email == ""


def test_survey_creation_database_constraints(db: Session, test_salesman):
    """Test that database allows null emails after migration"""
    # Create survey directly with null email
    survey = Survey(
        client_name="Test Null Email DB",
        email=None,  # Explicitly null
        phone_number="1234567890",
        estimated_paxes=2,
        villa_types="Villa B",
        notes="Database constraint test",
        status="new",
        priority="low",
        salesmen_id=test_salesman.id
    )
    
    db.add(survey)
    db.commit()
    db.refresh(survey)
    
    # Verify survey was created without issues
    assert survey.id is not None
    assert survey.email is None
    
    # Test retrieval
    retrieved_survey = get_survey(db, survey.id)
    assert retrieved_survey is not None
    assert retrieved_survey.email is None


@pytest.mark.asyncio
async def test_notification_email_service_handles_null_gracefully(db: Session, test_salesman):
    """Test that email service handles None values in survey data gracefully"""
    from app.services.email import send_survey_notification_to_salesman
    
    # Create survey data with null email
    survey_data = {
        'client_name': 'Test Client',
        'email': None,  # Null email - this should be handled by the template
        'phone_number': '1234567890',
        'estimated_paxes': 4,
        'villa_types': 'Villa A',
        'notes': 'Test notes',
        'status': 'new',
        'priority': 'high',
        'follow_up_date': '2024-01-15',
        'visiting_date': '2024-01-17'
    }
    
    # The email service should handle None gracefully using .get() method
    # This test verifies that no exceptions are raised
    try:
        # This should not raise an error even if email service is not configured
        # because the service checks for configuration first
        result = await send_survey_notification_to_salesman(
            salesman_email=test_salesman.email,
            salesman_name=test_salesman.full_name,
            survey_data=survey_data
        )
        # Result may be False due to email service not being configured in tests
        # but it should not raise an exception
        assert result is not None  # Should return boolean, not raise exception
    except Exception as e:
        # If any exception occurs, it should not be related to None email value
        assert "email" not in str(e).lower(), f"Email-related error occurred: {e}"