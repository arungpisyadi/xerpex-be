"""
Package schemas for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, condecimal


class PackageBase(BaseModel):
    """Base package schema"""
    name: str
    category: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    days: int = 1
    cost_per_pax: condecimal(max_digits=10, decimal_places=2) = 0.00
    min_pax: int = 1


class PackageCreate(PackageBase):
    """Package creation schema"""
    pass


class PackageUpdate(BaseModel):
    """Package update schema"""
    name: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    days: Optional[int] = None
    cost_per_pax: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    min_pax: Optional[int] = None


class Package(PackageBase):
    """Package schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class PackageListResponse(BaseModel):
    """Response schema for package list endpoint"""
    packages: List[Package]
    total: int
    skip: int
    limit: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class PackageResponse(Package):
    """Package response schema for API responses"""
    pass