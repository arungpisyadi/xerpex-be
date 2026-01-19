"""
Payment and Invoice schemas for the XerpeX ERP System
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, validator, field_validator, root_validator, computed_field

from app.schemas.villa import Villa


class InvoiceStatus(str, Enum):
    """Invoice status enumeration"""
    draft = "draft"
    sent = "sent"
    partially_paid = "partially_paid"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    partial = "partial"
    full = "full"


class PaymentMethod(str, Enum):
    """Payment method enumeration"""
    cash = "cash"
    bank_transfer = "bank_transfer"
    credit_card = "credit_card"
    debit_card = "debit_card"
    digital_wallet = "digital_wallet"
    check = "check"
    other = "other"


class PaymentType(str, Enum):
    """Payment type enumeration"""
    down_payment = "down-payment"
    installment = "installment"
    paid_off = "paid-off"


class InvoiceHistoryEventCategory(str, Enum):
    """Invoice history event category enumeration"""
    lifecycle = "lifecycle"
    status = "status"
    workflow = "workflow"
    payment = "payment"


# Invoice History Schemas
class InvoiceHistoryResponse(BaseModel):
    """Invoice history event response schema"""
    id: int
    event_type: str
    event_category: InvoiceHistoryEventCategory
    description: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    event_metadata: Optional[dict] = None
    created_at: datetime

    @computed_field
    @property
    def formatted_date(self) -> str:
        return self.created_at.strftime("%B %d, %Y at %I:%M %p")

    class Config:
        from_attributes = True


class InvoiceHistoryListResponse(BaseModel):
    """Response schema for invoice history endpoint"""
    invoice_id: int
    invoice_number: str
    history: List[InvoiceHistoryResponse]
    total_events: int
    skip: int
    limit: int

    class Config:
        from_attributes = True


# Payment History Schemas
class PaymentHistoryResponse(BaseModel):
    """Payment history event response schema"""
    id: int
    payment_id: int
    user_id: Optional[int]
    event_type: str
    event_category: str
    description: str
    event_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Payment Nested Schemas for Response Objects
class PaymentInvoiceNested(BaseModel):
    """Nested invoice information in payment response"""
    id: int
    invoice_number: str
    total: Decimal
    amount_due: Decimal
    status: InvoiceStatus
    issue_date: date
    due_date: date
    
    class Config:
        from_attributes = True


class PaymentCustomerNested(BaseModel):
    """Nested customer information in payment response"""
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaymentCreatorNested(BaseModel):
    """Nested creator (user) information in payment response"""
    id: int
    username: str
    full_name: Optional[str] = None
    email: str
    role: str
    
    class Config:
        from_attributes = True


class PaymentBookingNested(BaseModel):
    """Nested booking object for payment response"""
    id: int
    booking_code: str
    status: str
    check_in: date
    check_out: date
    total: Decimal
    total_pax: int
    
    class Config:
        from_attributes = True


# ============================================================================
# Invoice Villa Schemas
# ============================================================================

class InvoiceVillaBase(BaseModel):
    """Base invoice villa schema - simple junction table"""
    villa_id: int


class InvoiceVillaCreate(InvoiceVillaBase):
    """Invoice villa creation schema"""
    pass


class InvoiceVillaInDB(InvoiceVillaBase):
    """Invoice villa in database schema"""
    id: int
    invoice_id: int

    class Config:
        """Pydantic config"""
        from_attributes = True


class InvoiceVilla(InvoiceVillaInDB):
    """Invoice villa schema for API responses"""
    villa: Optional[Villa] = None  # Will be populated with Villa schema

    class Config:
        """Pydantic config"""
        from_attributes = True


# ============================================================================
# Invoice Item Schemas
# ============================================================================

class InvoiceItemBase(BaseModel):
    """Base invoice item schema"""
    package_id: int
    unit_price: Decimal = Field(..., gt=0, description="Unit price of the item")
    discount: Decimal = Field(default=Decimal('0.00'), ge=0, description="Discount amount")
    pax: int = 1
    line_total: Decimal = Field(..., gt=0, description="Total for this line item")

    @validator('pax')
    def validate_pax(cls, v):
        if v < 1:
            raise ValueError('pax must be at least 1')
        return v


class InvoiceItemCreate(InvoiceItemBase):
    """Invoice item creation schema"""
    pass


class InvoiceItemUpdate(BaseModel):
    """Invoice item update schema"""
    package_id: Optional[int] = None
    unit_price: Optional[Decimal] = Field(None, gt=0)
    discount: Optional[Decimal] = Field(None, ge=0)
    pax: Optional[int] = None
    line_total: Optional[Decimal] = Field(None, gt=0)


class InvoiceItemResponse(InvoiceItemBase):
    """Invoice item response schema"""
    id: int
    invoice_id: int
    package_name: Optional[str] = None
    created_at: datetime

    @root_validator(pre=True)
    def extract_package_name(cls, values):
        """Extract package name from the package relationship"""
        # If values is a SQLAlchemy model object, extract the package name
        if hasattr(values, 'package') and values.package and hasattr(values.package, 'name'):
            # Create a dict from the object and add the package_name
            if hasattr(values, '__dict__'):
                result = {k: v for k, v in values.__dict__.items() if not k.startswith('_')}
                result['package_name'] = values.package.name
                return result
        # If values is already a dict, check if it has a package key
        elif isinstance(values, dict) and 'package' in values:
            if values['package'] and hasattr(values['package'], 'name'):
                values['package_name'] = values['package'].name
        return values

    class Config:
        from_attributes = True


# ============================================================================
# Invoice Schemas
# ============================================================================

class InvoiceBase(BaseModel):
    """Base invoice schema"""
    customer_id: int
    issue_date: date = Field(default_factory=date.today)
    due_date: date
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    status: InvoiceStatus = InvoiceStatus.draft
    tax_total: Decimal = Field(default=Decimal('0.00'), ge=0)
    notes: Optional[str] = None

    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate that due_date is not before issue_date"""
        if 'issue_date' in values and v < values['issue_date']:
            raise ValueError('due_date cannot be before issue_date')
        return v


class InvoiceCreate(InvoiceBase):
    """Invoice creation schema"""
    sales_person_id: Optional[int] = None
    villas: List[int] = Field(default=[], validation_alias='villa_ids')
    items: List[InvoiceItemCreate] = Field(..., min_items=1)
    quote_id: Optional[int] = None  # For quote-to-invoice conversion
    payment_terms: Optional[str] = "Due on receipt"  # Optional with default value
    
    @field_validator('villas')
    @classmethod
    def validate_unique_villas(cls, v):
        """Ensure villas are unique"""
        if len(v) != len(set(v)):
            raise ValueError('villas must be unique')
        return v


class InvoiceUpdate(BaseModel):
    """Invoice update schema"""
    customer_id: Optional[int] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    status: Optional[InvoiceStatus] = None
    tax_total: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    villas: Optional[List[int]] = None
    items: Optional[List[InvoiceItemCreate]] = None
    
    @field_validator('villas')
    @classmethod
    def validate_unique_villas(cls, v):
        """Ensure villas are unique"""
        if v is not None and len(v) != len(set(v)):
            raise ValueError('villas must be unique')
        return v


class InvoiceStatusUpdate(BaseModel):
    """Invoice status update schema"""
    status: InvoiceStatus


class InvoiceNotesUpdate(BaseModel):
    """Invoice notes update schema"""
    notes: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    """Invoice response schema"""
    id: int
    user_id: int
    invoice_number: str
    quote_id: Optional[int] = None
    payment_terms: Optional[str] = None
    total: Decimal
    amount_due: Decimal
    amount_paid: Decimal
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    billing_address: Optional[str] = None
    items: List[InvoiceItemResponse] = []
    villas: List[InvoiceVilla] = []
    payments: List['PaymentResponse'] = []
    history: Optional[List[InvoiceHistoryResponse]] = []
    created_at: datetime
    updated_at: datetime

    @root_validator(pre=True)
    def extract_customer_data(cls, values):
        """Extract customer name, email, and billing address from the customer relationship"""
        # If values is a SQLAlchemy model object, extract the customer data
        if hasattr(values, 'customer') and values.customer:
            # Create a dict from the object and add the customer fields
            if hasattr(values, '__dict__'):
                result = {k: v for k, v in values.__dict__.items() if not k.startswith('_')}
                if hasattr(values.customer, 'name'):
                    result['customer_name'] = values.customer.name
                if hasattr(values.customer, 'email'):
                    result['customer_email'] = values.customer.email
                # Extract billing address with fallback
                billing_addr = values.customer.billing_address or values.customer.address
                result['billing_address'] = billing_addr
                return result
        # If values is already a dict, check if it has a customer key
        elif isinstance(values, dict) and 'customer' in values:
            if values['customer']:
                if hasattr(values['customer'], 'name'):
                    values['customer_name'] = values['customer'].name
                if hasattr(values['customer'], 'email'):
                    values['customer_email'] = values['customer'].email
                # Extract billing address with fallback
                billing_addr = values['customer'].billing_address or values['customer'].address
                values['billing_address'] = billing_addr
        return values

    class Config:
        from_attributes = True


# Payment Schemas
class PaymentBase(BaseModel):
    """Base payment schema"""
    invoice_id: int
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod
    payment_date: date = Field(default_factory=date.today)
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Payment creation schema"""
    status: PaymentStatus = Field(..., description="Payment status: partial (partial payment) or full (full payment)")
    payment_type: PaymentType = Field(..., description="Type of payment: down-payment, installment, or paid-off")


class PaymentUpdate(BaseModel):
    """Payment update schema"""
    amount: Optional[Decimal] = Field(None, gt=0)
    payment_method: Optional[PaymentMethod] = None
    payment_date: Optional[date] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    """Payment status update schema"""
    status: PaymentStatus


class PaymentResponse(PaymentBase):
    """Payment response schema"""
    id: int
    booking_id: Optional[int] = Field(None, description="ID of the booking associated with this payment")
    created_by: PaymentCreatorNested = Field(..., description="User who created the payment")
    booking: Optional[PaymentBookingNested] = Field(None, description="Nested booking object if payment is for a booking")
    payment_type: str = Field(..., description="Type of payment (down-payment, installment, or paid-off)")
    status: PaymentStatus = Field(..., description="Current status of the payment")
    invoice: Optional[PaymentInvoiceNested] = None
    customer: Optional[PaymentCustomerNested] = None
    history: List[PaymentHistoryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @root_validator(pre=True)
    def extract_nested_data(cls, values):
        """Extract nested relationship data from SQLAlchemy objects"""
        # If values is a SQLAlchemy model object, extract the nested data
        if hasattr(values, '__dict__'):
            # Define relationship attribute names to skip when copying scalar fields
            relationship_attrs = {'creator', 'booking', 'invoice', 'customer',
                                'invoice_history', 'payment_history', 'booking_history'}
            
            # Start with all scalar fields from the model
            result = {}
            for k, v in values.__dict__.items():
                # Skip SQLAlchemy internal fields starting with _
                if k.startswith('_'):
                    continue
                
                # Skip relationship attributes - we'll handle them separately
                if k in relationship_attrs:
                    continue
                
                # Include scalar database fields
                result[k] = v
            
            # Now extract and transform the nested relationship objects
            # Extract creator data
            if hasattr(values, 'creator') and values.creator:
                result['created_by'] = {
                    'id': values.creator.id,
                    'username': values.creator.username,
                    'full_name': values.creator.full_name,
                    'email': values.creator.email,
                    'role': values.creator.role
                }
            
            # Extract booking data
            if hasattr(values, 'booking') and values.booking:
                result['booking'] = {
                    'id': values.booking.id,
                    'booking_code': values.booking.booking_code,
                    'status': values.booking.status,
                    'check_in': values.booking.check_in,
                    'check_out': values.booking.check_out,
                    'total': values.booking.total,
                    'total_pax': values.booking.total_pax
                }
            
            # Extract invoice data
            if hasattr(values, 'invoice') and values.invoice:
                result['invoice'] = {
                    'id': values.invoice.id,
                    'invoice_number': values.invoice.invoice_number,
                    'total': values.invoice.total,
                    'amount_due': values.invoice.amount_due,
                    'status': values.invoice.status,
                    'issue_date': values.invoice.issue_date,
                    'due_date': values.invoice.due_date
                }
                
                # Extract customer data from invoice
                if hasattr(values.invoice, 'customer') and values.invoice.customer:
                    result['customer'] = {
                        'id': values.invoice.customer.id,
                        'name': values.invoice.customer.name,
                        'email': values.invoice.customer.email,
                        'phone': values.invoice.customer.phone_number,
                        'address': values.invoice.customer.address
                    }
            
            # Also check for direct customer property (from model @property)
            elif hasattr(values, 'customer') and values.customer:
                result['customer'] = {
                    'id': values.customer.id,
                    'name': values.customer.name,
                    'email': values.customer.email,
                    'phone': values.customer.phone_number,
                    'address': values.customer.address
                }
            
            # Map payment_history to history
            if hasattr(values, 'payment_history'):
                result['history'] = values.payment_history
            
            return result
        
        # If values is already a dict, check if it has nested objects
        elif isinstance(values, dict):
            # Extract creator data from dict
            if 'creator' in values and values['creator']:
                if hasattr(values['creator'], 'id'):
                    values['created_by'] = {
                        'id': values['creator'].id,
                        'username': values['creator'].username,
                        'full_name': values['creator'].full_name,
                        'email': values['creator'].email,
                        'role': values['creator'].role
                    }
            
            # Extract booking data from dict
            if 'booking' in values and values['booking']:
                if hasattr(values['booking'], 'booking_code'):
                    values['booking'] = {
                        'id': values['booking'].id,
                        'booking_code': values['booking'].booking_code,
                        'status': values['booking'].status,
                        'check_in': values['booking'].check_in,
                        'check_out': values['booking'].check_out,
                        'total': values['booking'].total,
                        'total_pax': values['booking'].total_pax
                    }
            
            # Extract invoice data from dict
            if 'invoice' in values and values['invoice']:
                if hasattr(values['invoice'], 'invoice_number'):
                    values['invoice'] = {
                        'id': values['invoice'].id,
                        'invoice_number': values['invoice'].invoice_number,
                        'total': values['invoice'].total,
                        'amount_due': values['invoice'].amount_due,
                        'status': values['invoice'].status,
                        'issue_date': values['invoice'].issue_date,
                        'due_date': values['invoice'].due_date
                    }
                    
                    # Extract customer data from invoice
                    if hasattr(values['invoice'], 'customer') and values['invoice'].customer:
                        values['customer'] = {
                            'id': values['invoice'].customer.id,
                            'name': values['invoice'].customer.name,
                            'email': values['invoice'].customer.email,
                            'phone': values['invoice'].customer.phone_number,
                            'address': values['invoice'].customer.address
                        }
            
            # Also check for direct customer in dict
            elif 'customer' in values and values['customer']:
                if hasattr(values['customer'], 'id'):
                    values['customer'] = {
                        'id': values['customer'].id,
                        'name': values['customer'].name,
                        'email': values['customer'].email,
                        'phone': values['customer'].phone_number,
                        'address': values['customer'].address
                    }
            
            # Map payment_history to history
            if 'payment_history' in values:
                values['history'] = values['payment_history']
        
        return values

    class Config:
        from_attributes = True


# Quote to Invoice Conversion
class QuoteToInvoiceRequest(BaseModel):
    """Quote to invoice conversion request schema"""
    quote_id: int
    issue_date: Optional[date] = Field(default_factory=date.today)
    due_date: date
    notes: Optional[str] = None


# Invoice to Booking Conversion
class InvoiceToBookingRequest(BaseModel):
    """Invoice to booking conversion request schema"""
    invoice_id: int
    check_in: date
    check_out: date
    total_pax: int = Field(default=1, gt=0)
    notes: Optional[str] = None
    
    @validator('check_out')
    def validate_check_out(cls, v, values):
        """Validate that check_out is after check_in"""
        if 'check_in' in values and v <= values['check_in']:
            raise ValueError('Check-out date must be after check-in date')
        return v


class InvoiceToBookingResponse(BaseModel):
    """Invoice to booking conversion response schema"""
    message: str
    booking_id: int
    booking_code: str
    invoice_id: int
    
    class Config:
        from_attributes = True


# Summary and Statistics Schemas
class InvoiceSummary(BaseModel):
    """Invoice summary schema"""
    total_invoices: int
    total_value: Decimal
    status_breakdown: dict
    overdue_count: int
    overdue_value: Decimal


class PaymentSummary(BaseModel):
    """Payment summary schema"""
    total_payments: int
    total_amount: Decimal
    method_breakdown: dict
    recent_payments: List[PaymentResponse]


class CustomerInvoiceSummary(BaseModel):
    """Customer invoice summary schema"""
    customer_id: int
    customer_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal
    invoice_count: int
    last_payment_date: Optional[date] = None


class InvoiceListResponse(BaseModel):
    """Response schema for invoice list endpoint"""
    invoices: List[InvoiceResponse]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    """Response schema for payment list endpoint"""
    payments: List[PaymentResponse]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True


class OverdueInvoicesResponse(BaseModel):
    """Response schema for overdue invoices endpoint"""
    overdue_invoices: List[InvoiceResponse]
    count: int

    class Config:
        from_attributes = True


class OverdueInvoicesCheckResponse(BaseModel):
    """Response schema for overdue invoices check endpoint"""
    overdue_count: int
    overdue_invoices: List[InvoiceResponse]

    class Config:
        from_attributes = True


class InvoicePaymentsResponse(BaseModel):
    """Response schema for invoice payments endpoint"""
    invoice_id: int
    payments: List[PaymentResponse]
    payment_summary: dict

    class Config:
        from_attributes = True


class PaymentReceiptResponse(BaseModel):
    """Response schema for payment receipt endpoint"""
    payment: PaymentResponse
    invoice: Optional[InvoiceResponse] = None
    customer: Optional[dict] = None
    company_info: dict
    formatted_payment_date: str
    formatted_amount: str
    payment_method_display: str
    status_display: str

    class Config:
        from_attributes = True


class PaymentMethodsResponse(BaseModel):
    """Response schema for payment methods endpoint"""
    payment_methods: List[dict]

    class Config:
        from_attributes = True


class InvoicePreviewResponse(BaseModel):
    """Response schema for invoice preview endpoint"""
    invoice: InvoiceResponse
    company_info: dict
    payment_summary: dict
    formatted_issue_date: str
    formatted_due_date: str
    status_display: str
    is_overdue: bool

    class Config:
        from_attributes = True


# Update forward references
InvoiceResponse.model_rebuild()