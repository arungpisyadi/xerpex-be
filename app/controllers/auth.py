"""
Authentication controllers for the XerpeX ERP System
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserResponse, UserLogin, UpdatePersonalInfo, UpdatePassword
from app.services.auth import authenticate_user, create_user, log_user_login, generate_token, update_personal_info, update_password
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token, deprecated=True)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint (DEPRECATED - Use /auth/login/json instead)
    
    This endpoint uses form data which is being deprecated in favor of JSON.
    
    Args:
        request: FastAPI request
        form_data: OAuth2 form data (username field is used for email)
        db: Database session
        
    Returns:
        Token: JWT token
        
    Raises:
        HTTPException: If authentication fails
    """
    # OAuth2PasswordRequestForm uses 'username' field, but our system uses email for authentication
    # So we treat the username field as email
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


@router.post("/login/json", response_model=Token)
async def login_json(
    request: Request,
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login endpoint with JSON body
    
    This is the preferred method for authentication.
    
    Args:
        request: FastAPI request
        user_login: User login data
        db: Database session
        
    Returns:
        Token: JWT token
        
    Raises:
        HTTPException: If authentication fails
    """
    # UserLogin schema uses email field, which we pass to authenticate_user
    # authenticate_user now accepts either username or email
    user = authenticate_user(db, user_login.email, user_login.password)
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


@router.post("/login-json", response_model=Token, deprecated=True)
async def login_json_deprecated(
    request: Request,
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login endpoint with JSON body (DEPRECATED - Use /auth/login/json instead)
    
    This endpoint is maintained for backward compatibility.
    
    Args:
        request: FastAPI request
        user_login: User login data
        db: Database session
        
    Returns:
        Token: JWT token
        
    Raises:
        HTTPException: If authentication fails
    """
    # Redirect to the new endpoint
    return await login_json(request, user_login, db)


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


@router.put("/profile/personal-info", response_model=UserResponse)
async def update_user_personal_info(
    update_data: UpdatePersonalInfo,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's personal information
    
    This endpoint allows authenticated users to update their personal information
    including full name, email, and phone number. At least one field must be provided.
    Email and phone uniqueness will be validated.
    
    Args:
        update_data: Personal information update data (full_name, email, phone)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserResponse: Updated user information
        
    Raises:
        HTTPException: If user not found, email already taken, phone already taken,
                      or validation fails
    """
    return await update_personal_info(db, current_user.id, update_data)


@router.put("/profile/password")
async def update_user_password(
    password_data: UpdatePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's password
    
    This endpoint allows authenticated users to change their password. The current
    password must be provided and verified before the new password is set. The new
    password must be at least 8 characters and different from the current password.
    
    Args:
        password_data: Password update data (current_password, new_password)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If user not found, current password is incorrect,
                      or validation fails
    """
    await update_password(db, current_user.id, password_data)
    return {"message": "Password updated successfully"}