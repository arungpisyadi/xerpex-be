"""
Authentication controllers for the XerpeX ERP System
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserResponse
from app.services.auth import authenticate_user, create_user, log_user_login, generate_token
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint
    
    Args:
        request: FastAPI request
        form_data: OAuth2 form data
        db: Database session
        
    Returns:
        Token: JWT token
        
    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log user login
    client_host = request.client.host if request.client else None
    log_user_login(db, user.id, client_host)
    
    # Generate token
    return generate_token(user)


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register endpoint
    
    Args:
        user_data: User data
        db: Database session
        
    Returns:
        UserResponse: Created user
        
    Raises:
        HTTPException: If user already exists
    """
    return create_user(db, user_data)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout endpoint
    
    Args:
        current_user: Current user
        
    Returns:
        dict: Success message
    """
    # In a stateless JWT system, we don't actually invalidate the token
    # Client should discard the token
    return {"success": True}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user info
    
    Args:
        current_user: Current user
        
    Returns:
        UserResponse: Current user info
    """
    return current_user