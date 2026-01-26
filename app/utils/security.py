"""
Security utilities for the XerpeX ERP System
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

# Password hashing context
# Configure bcrypt with specific settings to avoid version compatibility issues
# Monkey patch for bcrypt 4.x compatibility with passlib
import bcrypt
if not hasattr(bcrypt, '__about__'):
    bcrypt.__about__ = type('obj', (object,), {
        '__version__': bcrypt.__version__
    })

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",  # Use the 2b identifier which is widely supported
    bcrypt__min_rounds=12  # Set minimum rounds for security
)

oauth2_scheme = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Token expiration time
        
    Returns:
        str: JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Create a more complete token payload with standard JWT claims
    to_encode = {
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at time
        "sub": str(subject),  # Subject (user ID)
        "iss": settings.PROJECT_NAME,  # Issuer
        "jti": f"{subject}_{int(datetime.utcnow().timestamp())}"  # JWT ID (unique identifier)
    }
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        
        # Verify the token format before returning
        if not isinstance(encoded_jwt, str) or encoded_jwt.count('.') < 2:
            raise ValueError("Generated token has invalid format")
            
        return encoded_jwt
    except Exception as e:
        # Log the error but don't expose details to client
        print(f"Error generating JWT token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system error"
        )


async def get_current_user(
    db: Session = Depends(get_db), credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> User:
    """
    Get the current authenticated user
    
    Args:
        db: Database session
        credentials: HTTP Bearer credentials containing the JWT token
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract token from credentials
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Validate token format before attempting to decode
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token has the correct format (at least 2 segments separated by dots)
    if token.count('.') < 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        # Include the error message for better diagnostics
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to validate token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Try to get user by username first (for backward compatibility with existing tokens)
    user = db.query(User).filter(User.username == user_id).first()
    
    # If not found by username, try by ID (in case user_id is numeric)
    if user is None and user_id.isdigit():
        user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Get the current admin user
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current admin user
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def should_apply_user_isolation(user: User) -> bool:
    """
    Check if user isolation should be applied based on user role
    
    Args:
        user: Current user
        
    Returns:
        bool: True if user isolation should be applied, False for admin/finance roles
    """
    return user.role not in ["admin", "finance", "sales"]


def get_user_filter_condition(user: User, model_user_id_field):
    """
    Get the appropriate filter condition based on user role
    
    Args:
        user: Current user
        model_user_id_field: The user_id field of the model (e.g., Customer.user_id)
        
    Returns:
        SQLAlchemy condition or True (no filter for admin/finance)
    """
    if should_apply_user_isolation(user):
        return model_user_id_field == user.id
    return True  # No filter for admin/finance roles


def has_delete_permission(user: User) -> bool:
    """
    Check if user has permission to delete invoices
    Only admin and finance roles can delete.
    
    Args:
        user: Current user
        
    Returns:
        bool: True if user can delete invoices, False otherwise
    """
    return user.role in ["admin", "finance"]