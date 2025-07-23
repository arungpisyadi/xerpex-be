"""
Settings services for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.settings import GeneralSettings
from app.schemas.settings import GeneralSettingsCreate, GeneralSettingsUpdate
from app.utils.sentry import sentry_monitored_service


@sentry_monitored_service
def get_general_settings(db: Session) -> Optional[GeneralSettings]:
    """
    Get the general settings
    
    Args:
        db: Database session
        
    Returns:
        GeneralSettings: General settings or None
    """
    return db.query(GeneralSettings).first()


@sentry_monitored_service
def create_general_settings(db: Session, settings: GeneralSettingsCreate) -> GeneralSettings:
    """
    Create general settings
    
    Args:
        db: Database session
        settings: General settings data
        
    Returns:
        GeneralSettings: Created general settings
        
    Raises:
        HTTPException: If general settings already exist
    """
    # Check if general settings already exist
    existing_settings = get_general_settings(db)
    if existing_settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="General settings already exist. Use update instead."
        )
    
    # Create new general settings
    db_settings = GeneralSettings(
        company_name=settings.company_name,
        company_address=settings.company_address,
        company_phone=settings.company_phone,
        company_email=settings.company_email,
        bank_account_number=settings.bank_account_number,
        bank_account_holder_name=settings.bank_account_holder_name,
        bank_name=settings.bank_name,
        bank_swift_number=settings.bank_swift_number,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    
    return db_settings


@sentry_monitored_service
def update_general_settings(db: Session, settings_update: GeneralSettingsUpdate) -> GeneralSettings:
    """
    Update general settings
    
    Args:
        db: Database session
        settings_update: General settings update data
        
    Returns:
        GeneralSettings: Updated general settings
        
    Raises:
        HTTPException: If general settings do not exist
    """
    db_settings = get_general_settings(db)
    if not db_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="General settings not found. Create settings first."
        )
    
    # Update settings fields
    update_data = settings_update.dict(exclude_unset=True)
    
    # Update the settings
    for key, value in update_data.items():
        if value is not None:
            setattr(db_settings, key, value)
    
    db_settings.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(db_settings)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings due to database error"
        )
    
    return db_settings