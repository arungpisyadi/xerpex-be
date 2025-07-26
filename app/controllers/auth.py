"""
Authentication controllers for the XerpeX ERP System
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserResponse, UserLogin
from app.services.auth import authenticate_user, create_user, log_user_login, generate_token
from app.utils.security import get_current_active_user
from app.utils.sentry import capture_exception, get_request_info

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
    try:
        # Direct database query with timeout handling
        from sqlalchemy.sql import text
        from datetime import datetime, timedelta
        from app.utils.security import create_access_token
        from sqlalchemy.exc import SQLAlchemyError
        import logging
        
        # Set up logging
        logger = logging.getLogger(__name__)
        
        # Simple query to find user by email
        query = text("""
            SELECT id, email, password_hash, role
            FROM user
            WHERE email = :email OR username = :email
            LIMIT 1
        """)
        
        # Execute with explicit timeout
        try:
            # Set a statement timeout if using PostgreSQL or MySQL
            try:
                # PostgreSQL syntax
                db.execute(text("SET statement_timeout = 5000"))  # 5 seconds
            except:
                try:
                    # MySQL syntax
                    db.execute(text("SET max_execution_time = 5000"))  # 5 seconds
                except:
                    # If both fail, continue without setting timeout
                    pass
                
            # Execute the query
            result = db.execute(query, {"email": user_login.email}).fetchone()
        except SQLAlchemyError as e:
            # Log the database error
            logger.error(f"Database error during login: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation timed out",
            )
        
        # Check if user exists
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        from app.utils.security import verify_password
        if not verify_password(user_login.password, result.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Skip logging to avoid additional database operations
        
        # Generate token directly
        access_token_expires = timedelta(minutes=60)  # Short expiry for testing
        access_token = create_access_token(
            subject=result.id, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Return a generic error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login process failed: {str(e)}",
        )


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