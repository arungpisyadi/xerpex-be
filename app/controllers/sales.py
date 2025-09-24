"""
Sales controllers for the XerpeX ERP System
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import SalesUserResponse
from app.services.user import get_users
from app.utils.security import get_current_active_user

router = APIRouter(prefix="", tags=["sales"])


@router.get("/get-sales", response_model=List[SalesUserResponse])
async def get_sales_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all active sales users
    
    Args:
        db: Database session
        current_user: Current user
        
    Returns:
        List[SalesUserResponse]: List of sales users with minimal info
    """
    # Any authenticated user can access this endpoint
    users = get_users(db, role="sales", is_active=True)
    return users