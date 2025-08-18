"""
User services for the XerpeX ERP System
"""
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserActivity
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import get_password_hash
def get_user(db: Session, user_id: int) -> Optional[User]:
    """
    Get a user by ID
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        User: User or None
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get a user by email
    
    Args:
        db: Database session
        email: User email
        
    Returns:
        User: User or None
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Get a user by username
    
    Args:
        db: Database session
        username: Username
        
    Returns:
        User: User or None
    """
    return db.query(User).filter(User.username == username).first()


def get_users(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    role: Optional[str] = None,
    is_active: Optional[bool] = None
) -> List[User]:
    """
    Get users with optional filtering
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        role: Filter by role
        is_active: Filter by active status
        
    Returns:
        List[User]: List of users
    """
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    return query.offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> User:
    """
    Create a new user
    
    Args:
        db: Database session
        user: User data
        
    Returns:
        User: Created user
        
    Raises:
        HTTPException: If user already exists
    """
    # Check if user already exists
    db_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()
    
    if db_user:
        if db_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> User:
    """
    Update a user
    
    Args:
        db: Database session
        user_id: User ID
        user_update: User update data
        
    Returns:
        User: Updated user
        
    Raises:
        HTTPException: If user not found or email/username already taken
    """
    db_user = get_user(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if email is being updated and is already taken
    if user_update.email and user_update.email != db_user.email:
        existing_user = get_user_by_email(db, user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Check if username is being updated and is already taken
    if user_update.username and user_update.username != db_user.username:
        existing_user = get_user_by_username(db, user_update.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    
    # Handle password update separately
    if "password" in update_data:
        hashed_password = get_password_hash(update_data.pop("password"))
        update_data["password_hash"] = hashed_password
    
    # Update the user
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """
    Delete a user
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        bool: True if user was deleted
        
    Raises:
        HTTPException: If user not found
    """
    db_user = get_user(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(db_user)
    db.commit()
    
    return True


def get_user_activities(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> List[UserActivity]:
    """
    Get user activities
    
    Args:
        db: Database session
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[UserActivity]: List of user activities
        
    Raises:
        HTTPException: If user not found
    """
    db_user = get_user(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return db.query(UserActivity).filter(
        UserActivity.user_id == user_id
    ).order_by(
        UserActivity.created_at.desc()
    ).offset(skip).limit(limit).all()