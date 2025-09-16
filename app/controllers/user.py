"""
User controllers for the XerpeX ERP System
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate, UserActivity
from app.services.user import (
    get_user, get_users, create_user, update_user, delete_user, get_user_activities
)
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserSchema])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all users with optional filtering
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        role: Filter by role
        is_active: Filter by active status
        db: Database session
        current_user: Current user
        
    Returns:
        List[User]: List of users
    """
    # Only admin and manager can list all users
    if current_user.role not in ["admin", "manager", "sales"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    users = get_users(db, skip=skip, limit=limit, role=role, is_active=is_active)
    return users


@router.post("", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new user
    
    Args:
        user: User data
        db: Database session
        current_user: Current user
        
    Returns:
        User: Created user
        
    Raises:
        HTTPException: If user already exists or not enough permissions
    """
    # Only admin can create users
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return create_user(db=db, user=user)


@router.get("/{user_id}", response_model=UserSchema)
async def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a user by ID
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Current user
        
    Returns:
        User: User
        
    Raises:
        HTTPException: If user not found or not enough permissions
    """
    # Users can only see their own profile unless they are admin or manager
    if current_user.id != user_id and current_user.role not in ["admin", "manager", "sales"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db_user = get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a user
    
    Args:
        user_id: User ID
        user_update: User update data
        db: Database session
        current_user: Current user
        
    Returns:
        User: Updated user
        
    Raises:
        HTTPException: If user not found or not enough permissions
    """
    # Users can only update their own profile unless they are admin
    # Only admin can update roles
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Only admin can update role
    if user_update.role is not None and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to change role"
        )
    
    return update_user(db=db, user_id=user_id, user_update=user_update)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a user
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Current user
        
    Raises:
        HTTPException: If user not found or not enough permissions
    """
    # Only admin can delete users
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Prevent admin from deleting themselves
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    delete_user(db=db, user_id=user_id)
    return None


@router.get("/{user_id}/activities", response_model=List[UserActivity])
async def read_user_activities(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user activities
    
    Args:
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current user
        
    Returns:
        List[UserActivity]: List of user activities
        
    Raises:
        HTTPException: If user not found or not enough permissions
    """
    # Users can only see their own activities unless they are admin or manager
    if current_user.id != user_id and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    activities = get_user_activities(db=db, user_id=user_id, skip=skip, limit=limit)
    return activities