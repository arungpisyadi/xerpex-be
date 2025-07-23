"""
Payment controller for the XerpeX ERP System
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payment import Payment, PaymentInvoice
from app.schemas.payment import (
    PaymentCreate, PaymentUpdate, PaymentResponse, PaymentDetailResponse,
    PaymentStatusUpdate, PaymentInvoiceCreate, PaymentInvoiceUpdate, PaymentInvoiceResponse
)
from app.services.payment import (
    get_payment, get_payments, create_payment, update_payment,
    update_payment_status, delete_payment, get_payment_details,
    get_invoice, get_invoices, create_invoice, update_invoice,
    update_invoice_status, delete_invoice, link_payment_to_invoice,
    get_booking_payment_summary
)
from app.utils.security import get_current_active_user, get_current_admin_user


router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(get_current_active_user)]
)


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment_endpoint(
    payment: PaymentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Create a new payment
    """
    return create_payment(db, payment, current_user.id)


@router.get("/", response_model=List[PaymentResponse])
def read_payments(
    skip: int = 0,
    limit: int = 100,
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get all payments with optional filtering
    """
    return get_payments(
        db, 
        skip=skip, 
        limit=limit,
        booking_id=booking_id,
        status=status,
        payment_method=payment_method,
        from_date=from_date,
        to_date=to_date
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
def read_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get a payment by ID
    """
    db_payment = get_payment(db, payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment


@router.get("/{payment_id}/details", response_model=PaymentDetailResponse)
def read_payment_details(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get detailed payment information
    """
    return get_payment_details(db, payment_id)


@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment_endpoint(
    payment_id: int,
    payment_update: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Update a payment
    """
    return update_payment(db, payment_id, payment_update)


@router.patch("/{payment_id}/status", response_model=PaymentResponse)
def update_payment_status_endpoint(
    payment_id: int,
    status_update: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Update a payment status
    """
    return update_payment_status(db, payment_id, status_update)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Delete a payment (admin only)
    """
    delete_payment(db, payment_id)
    return {"detail": "Payment deleted successfully"}


@router.post("/{payment_id}/link-invoice/{invoice_id}", response_model=PaymentResponse)
def link_payment_to_invoice_endpoint(
    payment_id: int,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Link a payment to an invoice
    """
    return link_payment_to_invoice(db, payment_id, invoice_id)


# Invoice endpoints
@router.post("/invoices", response_model=PaymentInvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice_endpoint(
    invoice: PaymentInvoiceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Create a new invoice
    """
    return create_invoice(db, invoice, current_user.id)


@router.get("/invoices", response_model=List[PaymentInvoiceResponse])
def read_invoices(
    skip: int = 0,
    limit: int = 100,
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    guest_name: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get all invoices with optional filtering
    """
    return get_invoices(
        db, 
        skip=skip, 
        limit=limit,
        booking_id=booking_id,
        status=status,
        guest_name=guest_name,
        from_date=from_date,
        to_date=to_date
    )


@router.get("/invoices/{invoice_id}", response_model=PaymentInvoiceResponse)
def read_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get an invoice by ID
    """
    db_invoice = get_invoice(db, invoice_id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice


@router.put("/invoices/{invoice_id}", response_model=PaymentInvoiceResponse)
def update_invoice_endpoint(
    invoice_id: int,
    invoice_update: PaymentInvoiceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Update an invoice
    """
    return update_invoice(db, invoice_id, invoice_update)


@router.patch("/invoices/{invoice_id}/status", response_model=PaymentInvoiceResponse)
def update_invoice_status_endpoint(
    invoice_id: int,
    status_update: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Update an invoice status
    """
    return update_invoice_status(db, invoice_id, status_update.status)


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice_endpoint(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Delete an invoice (admin only)
    """
    delete_invoice(db, invoice_id)
    return {"detail": "Invoice deleted successfully"}


# Booking payment summary
@router.get("/bookings/{booking_id}/summary")
def get_booking_payment_summary_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get payment summary for a booking
    """
    return get_booking_payment_summary(db, booking_id)