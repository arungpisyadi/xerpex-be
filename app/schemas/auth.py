"""
Authentication schemas for the XerpeX ERP System
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


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
    phone: Optional[str] = None
    
    class Config:
        """Pydantic config"""
        from_attributes = True


class UpdatePersonalInfo(BaseModel):
    """Update personal information schema"""
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    
    @model_validator(mode='after')
    def validate_at_least_one_field(self):
        """Ensure at least one field is provided for update"""
        if not any([self.full_name, self.email, self.phone]):
            raise ValueError('At least one field must be provided for update')
        return self


class UpdatePassword(BaseModel):
    """Update password schema"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v, info):
        """Ensure new password is different from current password"""
        if 'current_password' in info.data and v == info.data['current_password']:
            raise ValueError('New password must be different from current password')
        return v