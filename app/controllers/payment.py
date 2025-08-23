"""
Payment API controllers for the XerpeX ERP System
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.payment import (
    PaymentCreate, PaymentUpdate, PaymentStatusUpdate, PaymentResponse,
    PaymentStatus, PaymentMethod, PaymentListResponse, InvoicePaymentsResponse,
    PaymentReceiptResponse, PaymentMethodsResponse
)
from app.services.payment import (
    get_payment, get_payments, create_payment, update_payment,
    update_payment_status, delete_payment, get_payment_statistics
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    payment_method: Optional[PaymentMethod] = Query(None, description="Filter by payment method"),
    from_date: Optional[date] = Query(None, description="Filter by payment date from"),
    to_date: Optional[date] = Query(None, description="Filter by payment date to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of payments with optional filtering
    """
    payments = get_payments(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        invoice_id=invoice_id,
        status=status,
        payment_method=payment_method,
        from_date=from_date,
        to_date=to_date
    )
    
    # Get total count for pagination
    total_payments = len(get_payments(
        db=db,
        current_user=current_user,
        skip=0,
        limit=10000,
        invoice_id=invoice_id,
        status=status,
        payment_method=payment_method,
        from_date=from_date,
        to_date=to_date
    ))
    
    return {
        "payments": payments,
        "total": total_payments,
        "skip": skip,
        "limit": limit
    }


@router.get("/statistics", response_model=dict)
async def get_payment_statistics_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payment statistics for dashboard
    """
    stats = get_payment_statistics(db=db, user_id=current_user.id)
    return stats


@router.get("/methods", response_model=PaymentMethodsResponse)
async def get_payment_methods():
    """
    Get available payment methods
    """
    return {
        "payment_methods": [
            {"value": method.value, "label": method.value.replace("_", " ").title()}
            for method in PaymentMethod
        ]
    }


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_endpoint(
    payment: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new payment
    """
    try:
        db_payment = create_payment(
            db=db,
            payment=payment,
            user_id=current_user.id
        )
        return db_payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific payment by ID
    """
    payment = get_payment(db=db, payment_id=payment_id, current_user=current_user)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return payment


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment_endpoint(
    payment_id: int,
    payment_update: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a payment
    """
    try:
        updated_payment = update_payment(
            db=db,
            payment_id=payment_id,
            payment_update=payment_update,
            user_id=current_user.id
        )
        return updated_payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{payment_id}/status", response_model=PaymentResponse)
async def update_payment_status_endpoint(
    payment_id: int,
    status_update: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update payment status
    """
    try:
        updated_payment = update_payment_status(
            db=db,
            payment_id=payment_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a payment
    """
    success = delete_payment(
        db=db,
        payment_id=payment_id,
        user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )


# Payment Workflow Actions
@router.post("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirm a payment (change status to completed)
    """
    status_update = PaymentStatusUpdate(status=PaymentStatus.completed)
    try:
        updated_payment = update_payment_status(
            db=db,
            payment_id=payment_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{payment_id}/fail", response_model=PaymentResponse)
async def fail_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a payment as failed
    """
    status_update = PaymentStatusUpdate(status=PaymentStatus.failed)
    try:
        updated_payment = update_payment_status(
            db=db,
            payment_id=payment_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Refund a payment
    """
    status_update = PaymentStatusUpdate(status=PaymentStatus.refunded)
    try:
        updated_payment = update_payment_status(
            db=db,
            payment_id=payment_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/invoice/{invoice_id}", response_model=InvoicePaymentsResponse)
async def get_invoice_payments(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all payments for a specific invoice
    """
    payments = get_payments(
        db=db,
        current_user=current_user,
        invoice_id=invoice_id,
        skip=0,
        limit=1000
    )
    
    # Calculate payment summary
    from decimal import Decimal
    total_paid = sum(
        payment.amount for payment in payments 
        if payment.status == PaymentStatus.completed
    )
    
    pending_amount = sum(
        payment.amount for payment in payments 
        if payment.status == PaymentStatus.pending
    )
    
    return {
        "invoice_id": invoice_id,
        "payments": payments,
        "payment_summary": {
            "total_payments": len(payments),
            "total_paid": total_paid,
            "pending_amount": pending_amount,
            "completed_payments": len([p for p in payments if p.status == PaymentStatus.completed]),
            "pending_payments": len([p for p in payments if p.status == PaymentStatus.pending])
        }
    }


@router.get("/{payment_id}/receipt", response_model=PaymentReceiptResponse)
async def get_payment_receipt(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payment receipt data for PDF generation or display
    """
    payment = get_payment(db=db, payment_id=payment_id, current_user=current_user)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Return formatted data for receipt generation
    return {
        "payment": payment,
        "invoice": payment.invoice,
        "customer": payment.invoice.customer if payment.invoice else None,
        "company_info": {
            "name": current_user.company_name or "Your Company",
            "email": current_user.email,
            # Add more company details as needed
        },
        "formatted_payment_date": payment.payment_date.strftime("%B %d, %Y"),
        "formatted_amount": f"${payment.amount:,.2f}",
        "payment_method_display": payment.payment_method.replace("_", " ").title(),
        "status_display": payment.status.title()
    }