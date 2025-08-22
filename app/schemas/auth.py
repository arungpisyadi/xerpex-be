"""
Authentication schemas for the XerpeX ERP System
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, model_validator


class Token(BaseModel):
    """Token schema"""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Token payload schema"""
    sub: Optional[int] = None


class UserLogin(BaseModel):
    """User login schema"""
    email: Optional[EmailStr] = None
    username: Optional[EmailStr] = None
    password: str
    
    @model_validator(mode='before')
    @classmethod
    def validate_email_or_username(cls, values):
        """Custom validation to ensure either email or username is provided"""
        if isinstance(values, dict):
            email = values.get('email')
            username = values.get('username')
            
            if not email and not username:
                raise ValueError('Either email or username must be provided')
            
            # If username is provided but not email, use username as email
            if username and not email:
                values['email'] = username
                
        return values


class UserCreate(BaseModel):
    """User creation schema"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool
    
    class Config:
        """Pydantic config"""
        from_attributes = True