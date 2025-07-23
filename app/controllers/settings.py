"""
Settings controllers for the XerpeX ERP System
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.settings import GeneralSettings as GeneralSettingsSchema
from app.schemas.settings import GeneralSettingsCreate, GeneralSettingsUpdate
from app.services.settings import (
    get_general_settings, create_general_settings, update_general_settings
)
from app.utils.security import get_current_active_user
from app.utils.sentry import sentry_monitored_controller

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/general", response_model=GeneralSettingsSchema)
@sentry_monitored_controller
async def read_general_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get general settings
    
    Args:
        db: Database session
        current_user: Current user
        
    Returns:
        GeneralSettings: General settings
        
    Raises:
        HTTPException: If general settings not found
    """
    settings = get_general_settings(db)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="General settings not found"
        )
    return settings


@router.post("/general", response_model=GeneralSettingsSchema, status_code=status.HTTP_201_CREATED)
@sentry_monitored_controller
async def create_general_settings_endpoint(
    settings: GeneralSettingsCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create general settings
    
    Args:
        settings: General settings data
        db: Database session
        current_user: Current user
        
    Returns:
        GeneralSettings: Created general settings
        
    Raises:
        HTTPException: If not enough permissions or general settings already exist
    """
    # Only admin can create general settings
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return create_general_settings(db=db, settings=settings)


@router.put("/general", response_model=GeneralSettingsSchema)
@sentry_monitored_controller
async def update_general_settings_endpoint(
    settings_update: GeneralSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update general settings
    
    Args:
        settings_update: General settings update data
        db: Database session
        current_user: Current user
        
    Returns:
        GeneralSettings: Updated general settings
        
    Raises:
        HTTPException: If not enough permissions or general settings not found
    """
    # Only admin can update general settings
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return update_general_settings(db=db, settings_update=settings_update)