"""
Salesmen controllers for the XerpeX ERP System
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.salesmen import Salesmen as SalesmenSchema, SalesmenCreate, SalesmenUpdate, SalesmenSummary
from app.services.salesmen import (
    get_salesman, get_salesmen, create_salesman, update_salesman, delete_salesman,
    get_active_salesmen_for_dropdown
)
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/salesmen", tags=["salesmen"])


@router.get("", response_model=List[SalesmenSchema])
async def read_salesmen(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all salesmen with optional filtering
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        is_active: Filter by active status
        db: Database session
        current_user: Current user
        
    Returns:
        List[Salesmen]: List of salesmen
    """
    # Only admin and manager can list all salesmen
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    salesmen = get_salesmen(db, skip=skip, limit=limit, is_active=is_active)
    return salesmen


@router.post("", response_model=SalesmenSchema, status_code=status.HTTP_201_CREATED)
async def create_new_salesman(
    salesman: SalesmenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new salesman
    
    Args:
        salesman: Salesman data
        db: Database session
        current_user: Current user
        
    Returns:
        Salesmen: Created salesman
        
    Raises:
        HTTPException: If salesman already exists or not enough permissions
    """
    # Only admin can create salesmen
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return create_salesman(db=db, salesman=salesman)


@router.get("/dropdown", response_model=List[SalesmenSummary])
async def read_salesmen_dropdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get active salesmen for dropdown/select options
    
    Args:
        db: Database session
        current_user: Current user
        
    Returns:
        List[SalesmenSummary]: List of active salesmen for dropdown
    """
    # All authenticated users can access dropdown
    salesmen = get_active_salesmen_for_dropdown(db)
    return salesmen


@router.get("/{salesman_id}", response_model=SalesmenSchema)
async def read_salesman(
    salesman_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a salesman by ID
    
    Args:
        salesman_id: Salesman ID
        db: Database session
        current_user: Current user
        
    Returns:
        Salesmen: Salesman
        
    Raises:
        HTTPException: If salesman not found or not enough permissions
    """
    # Only admin and manager can view salesman details
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db_salesman = get_salesman(db, salesman_id=salesman_id)
    if db_salesman is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )
    return db_salesman


@router.put("/{salesman_id}", response_model=SalesmenSchema)
async def update_salesman_endpoint(
    salesman_id: int,
    salesman_update: SalesmenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a salesman
    
    Args:
        salesman_id: Salesman ID
        salesman_update: Salesman update data
        db: Database session
        current_user: Current user
        
    Returns:
        Salesmen: Updated salesman
        
    Raises:
        HTTPException: If salesman not found or not enough permissions
    """
    # Only admin can update salesmen
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return update_salesman(db=db, salesman_id=salesman_id, salesman_update=salesman_update)


@router.delete("/{salesman_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_salesman_endpoint(
    salesman_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a salesman
    
    Args:
        salesman_id: Salesman ID
        db: Database session
        current_user: Current user
        
    Raises:
        HTTPException: If salesman not found or not enough permissions
    """
    # Only admin can delete salesmen
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    delete_salesman(db=db, salesman_id=salesman_id)
    return None