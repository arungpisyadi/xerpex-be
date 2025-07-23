"""
Authentication schemas for the XerpeX ERP System
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Token schema"""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Token payload schema"""
    sub: Optional[int] = None


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str


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