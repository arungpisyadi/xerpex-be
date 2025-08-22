"""
User schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool = True


class UserCreate(UserBase):
    """User creation schema"""
    password: str


class UserUpdate(BaseModel):
    """User update schema"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    """User in database schema"""
    id: int
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class User(UserInDB):
    """User schema"""
    pass


class UserActivityBase(BaseModel):
    """Base user activity schema"""
    activity_type: str
    description: str
    ip_address: Optional[str] = None


class UserActivityCreate(UserActivityBase):
    """User activity creation schema"""
    user_id: int


class UserActivity(UserActivityBase):
    """User activity schema"""
    id: int
    user_id: int
    created_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class UserWithActivities(User):
    """User with activities schema"""
    activities: List[UserActivity] = []


class UserListResponse(BaseModel):
    """Response schema for user list endpoint"""
    users: List[User]
    total: int
    skip: int
    limit: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class UserResponse(User):
    """User response schema for API responses"""
    pass