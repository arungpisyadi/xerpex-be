"""
Settings services for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.settings import GeneralSettings
from app.schemas.settings import GeneralSettingsCreate, GeneralSettingsUpdate

def get_general_settings(db: Session) -> Optional[GeneralSettings]:
    """
    Get the general settings
    
    Args:
        db: Database session
        
    Returns:
        GeneralSettings: General settings or None
    """
    return db.query(GeneralSettings).first()


def upsert_general_settings(db: Session, settings_data: GeneralSettingsCreate) -> GeneralSettings:
    """
    Create or update general settings (upsert operation)
    
    Args:
        db: Database session
        settings_data: General settings data
        
    Returns:
        GeneralSettings: Created or updated general settings
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Check if general settings already exist
        existing_settings = get_general_settings(db)
        
        if existing_settings:
            # Update existing settings
            existing_settings.company_name = settings_data.company_name
            existing_settings.company_address = settings_data.company_address
            existing_settings.company_phone = settings_data.company_phone
            existing_settings.company_email = settings_data.company_email
            existing_settings.bank_account_number = settings_data.bank_account_number
            existing_settings.bank_account_holder_name = settings_data.bank_account_holder_name
            existing_settings.bank_name = settings_data.bank_name
            existing_settings.bank_swift_number = settings_data.bank_swift_number
            existing_settings.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_settings)
            return existing_settings
        else:
            # Create new general settings
            db_settings = GeneralSettings(
                company_name=settings_data.company_name,
                company_address=settings_data.company_address,
                company_phone=settings_data.company_phone,
                company_email=settings_data.company_email,
                bank_account_number=settings_data.bank_account_number,
                bank_account_holder_name=settings_data.bank_account_holder_name,
                bank_name=settings_data.bank_name,
                bank_swift_number=settings_data.bank_swift_number,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(db_settings)
            db.commit()
            db.refresh(db_settings)
            return db_settings
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}"
        )


def create_general_settings(db: Session, settings: GeneralSettingsCreate) -> GeneralSettings:
    """
    Create general settings (deprecated - use upsert_general_settings instead)
    
    Args:
        db: Database session
        settings: General settings data
        
    Returns:
        GeneralSettings: Created general settings
    """
    return upsert_general_settings(db, settings)


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