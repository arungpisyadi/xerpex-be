"""
Quote schemas for the XerpeX ERP System
"""
from datetime import datetime, date
from typing import Optional, List, Literal
from pydantic import BaseModel, condecimal, validator
from app.schemas.customer import Customer
from app.schemas.package import Package


# Quote status type
QuoteStatus = Literal["draft", "sent", "accepted", "declined", "expired"]


class QuoteItemBase(BaseModel):
    """Base quote item schema"""
    package_id: int
    unit_price: condecimal(max_digits=10, decimal_places=2)
    discount: condecimal(max_digits=10, decimal_places=2) = 0.00
    line_total: condecimal(max_digits=10, decimal_places=2)

    @validator('line_total')
    def validate_line_total(cls, v, values):
        if 'unit_price' in values and 'discount' in values:
            expected_total = values['unit_price'] - values['discount']
            if abs(float(v) - float(expected_total)) > 0.01:  # Allow small floating point differences
                raise ValueError('Line total must equal unit_price minus discount')
        return v


class QuoteItemCreate(QuoteItemBase):
    """Quote item creation schema"""
    pass


class QuoteItemUpdate(BaseModel):
    """Quote item update schema"""
    package_id: Optional[int] = None
    unit_price: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    discount: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    line_total: Optional[condecimal(max_digits=10, decimal_places=2)] = None


class QuoteItemInDB(QuoteItemBase):
    """Quote item in database schema"""
    id: int
    quote_id: int
    created_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class QuoteItem(QuoteItemInDB):
    """Quote item schema for API responses"""
    package: Optional[Package] = None

    class Config:
        """Pydantic config"""
        from_attributes = True


class QuoteBase(BaseModel):
    """Base quote schema"""
    customer_id: int
    issue_date: date
    expiry_date: date
    status: QuoteStatus = "draft"
    total: condecimal(max_digits=10, decimal_places=2) = 0.00
    tax_total: condecimal(max_digits=10, decimal_places=2) = 0.00

    @validator('expiry_date')
    def validate_expiry_date(cls, v, values):
        if 'issue_date' in values and v <= values['issue_date']:
            raise ValueError('Expiry date must be after issue date')
        return v


class QuoteCreate(QuoteBase):
    """Quote creation schema"""
    items: List[QuoteItemCreate] = []


class QuoteUpdate(BaseModel):
    """Quote update schema"""
    customer_id: Optional[int] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[QuoteStatus] = None
    total: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    tax_total: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    items: Optional[List[QuoteItemCreate]] = None

    @validator('expiry_date')
    def validate_expiry_date(cls, v, values):
        if v is not None and 'issue_date' in values and values['issue_date'] is not None:
            if v <= values['issue_date']:
                raise ValueError('Expiry date must be after issue date')
        return v


class QuoteStatusUpdate(BaseModel):
    """Quote status update schema"""
    status: QuoteStatus


class QuoteInDB(QuoteBase):
    """Quote in database schema"""
    id: int
    user_id: int
    quote_number: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class Quote(QuoteInDB):
    """Quote schema for API responses"""
    customer: Optional[Customer] = None
    items: List[QuoteItem] = []

    class Config:
        """Pydantic config"""
        from_attributes = True


class QuoteDetail(Quote):
    """Detailed quote schema with all relationships"""
    pass


class QuoteSummary(BaseModel):
    """Quote summary schema for lists"""
    id: int
    quote_number: str
    customer_name: str
    issue_date: date
    expiry_date: date
    status: QuoteStatus
    total: condecimal(max_digits=10, decimal_places=2)
    created_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


class QuoteConversionRequest(BaseModel):
    """Schema for converting quote to invoice"""
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None

    @validator('due_date')
    def validate_due_date(cls, v):
        if v is not None and v <= date.today():
            raise ValueError('Due date must be in the future')
        return v


class QuoteListResponse(BaseModel):
    """Response schema for quote list endpoint"""
    quotes: List[Quote]
    total: int
    skip: int
    limit: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class QuoteCalculationResponse(BaseModel):
    """Response schema for quote calculation endpoint"""
    subtotal: condecimal(max_digits=10, decimal_places=2)
    tax_total: condecimal(max_digits=10, decimal_places=2)
    total: condecimal(max_digits=10, decimal_places=2)
    taxes_applied: List[dict] = []

    class Config:
        """Pydantic config"""
        from_attributes = True


class ExpiredQuotesResponse(BaseModel):
    """Response schema for expired quotes check endpoint"""
    expired_count: int
    expired_quotes: List[Quote]

    class Config:
        """Pydantic config"""
        from_attributes = True


class QuoteConversionResponse(BaseModel):
    """Response schema for quote to invoice conversion"""
    message: str
    invoice_id: int
    invoice_number: str

    class Config:
        """Pydantic config"""
        from_attributes = True


class QuotePreviewResponse(BaseModel):
    """Response schema for quote preview endpoint"""
    quote: Quote
    company_info: dict
    formatted_date: str
    formatted_expiry: Optional[str] = None
    status_display: str

    class Config:
        """Pydantic config"""
        from_attributes = True