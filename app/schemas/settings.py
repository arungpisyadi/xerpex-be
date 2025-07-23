"""
Settings schemas for the XerpeX ERP System
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr


class GeneralSettingsBase(BaseModel):
    """Base general settings schema"""
    company_name: str
    company_address: str
    company_phone: str
    company_email: EmailStr
    
    # Bank account details
    bank_account_number: str
    bank_account_holder_name: str
    bank_name: str
    bank_swift_number: str | None = None


class GeneralSettingsCreate(GeneralSettingsBase):
    """General settings creation schema"""
    pass


class GeneralSettingsUpdate(BaseModel):
    """General settings update schema"""
    company_name: str | None = None
    company_address: str | None = None
    company_phone: str | None = None
    company_email: EmailStr | None = None
    
    # Bank account details
    bank_account_number: str | None = None
    bank_account_holder_name: str | None = None
    bank_name: str | None = None
    bank_swift_number: str | None = None


class GeneralSettings(GeneralSettingsBase):
    """General settings schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True