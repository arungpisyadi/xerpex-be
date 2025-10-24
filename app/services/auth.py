"""
Authentication services for the XerpeX ERP System
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserActivity
from app.schemas.auth import UserCreate, UpdatePersonalInfo, UpdatePassword
from app.utils.security import verify_password, get_password_hash, create_access_token
def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[User]:
    """
    Authenticate a user using either username or email
    
    Args:
        db: Database session
        username_or_email: User username or email
        password: User password
        
    Returns:
        User: Authenticated user or None
    """
    # Try to find user by email first, then by username if not found
    user = db.query(User).filter(
        (User.email == username_or_email) | (User.username == username_or_email)
    ).first()
    
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user
    
    Args:
        db: Database session
        user_data: User data
        
    Returns:
        User: Created user
        
    Raises:
        HTTPException: If user already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    if existing_user:
        if existing_user.email == user_data.email:
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
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log user creation
    activity = UserActivity(
        user_id=db_user.id,
        activity_type="registration",
        description="User account created",
        created_at=datetime.utcnow()
    )
    db.add(activity)
    db.commit()
    
    return db_user


def log_user_login(db: Session, user_id: int, ip_address: Optional[str] = None) -> None:
    """
    Log user login
    
    Args:
        db: Database session
        user_id: User ID
        ip_address: IP address
    """
    # Update user last login
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.last_login = datetime.utcnow()
        
        # Log login activity
        activity = UserActivity(
            user_id=user_id,
            activity_type="login",
            description="User logged in",
            ip_address=ip_address,
            created_at=datetime.utcnow()
        )
        db.add(activity)
        db.commit()


def generate_token(user: User) -> dict:
    """
    Generate JWT token for user
    
    Args:
        user: User
        
    Returns:
        dict: Token data
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


async def update_personal_info(db: Session, user_id: int, update_data: UpdatePersonalInfo) -> User:
    """
    Update user's personal information
    
    Args:
        db: Database session
        user_id: User ID
        update_data: Personal information update data
        
    Returns:
        User: Updated user object
        
    Raises:
        HTTPException: If user not found, email already taken, or phone already taken
    """
    # Get the user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if email is being updated and if it's already taken by another user
    if update_data.email is not None and update_data.email != user.email:
        existing_user = db.query(User).filter(
            User.email == update_data.email,
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered by another user"
            )
    
    # Check if phone is being updated and if it's already taken by another user
    if update_data.phone is not None and update_data.phone != user.phone:
        existing_user = db.query(User).filter(
            User.phone == update_data.phone,
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered by another user"
            )
    
    # Update only the fields that are provided (not None)
    if update_data.full_name is not None:
        user.full_name = update_data.full_name
    if update_data.email is not None:
        user.email = update_data.email
    if update_data.phone is not None:
        user.phone = update_data.phone
    
    # Update the updated_at timestamp
    user.updated_at = datetime.utcnow()
    
    try:
        # Commit changes and refresh
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update personal information: {str(e)}"
        )


async def update_password(db: Session, user_id: int, password_data: UpdatePassword) -> User:
    """
    Update user's password
    
    Args:
        db: Database session
        user_id: User ID
        password_data: Password update data containing current and new password
        
    Returns:
        User: Updated user object
        
    Raises:
        HTTPException: If user not found, current password is incorrect, or database error occurs
    """
    # Get the user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify the current password
    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Hash the new password
    hashed_password = get_password_hash(password_data.new_password)
    
    # Update user's password_hash field
    user.password_hash = hashed_password
    
    # Update the updated_at timestamp
    user.updated_at = datetime.utcnow()
    
    try:
        # Commit changes
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update password: {str(e)}"
        )