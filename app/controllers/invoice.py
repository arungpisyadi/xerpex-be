"""
Invoice API controllers for the XerpeX ERP System
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.payment import (
    InvoiceCreate, InvoiceUpdate, InvoiceStatusUpdate, InvoiceNotesUpdate, InvoiceResponse,
    InvoiceStatus, QuoteToInvoiceRequest, InvoiceListResponse,
    OverdueInvoicesResponse, OverdueInvoicesCheckResponse, InvoicePreviewResponse,
    InvoiceHistoryListResponse, InvoiceHistoryEventCategory
)
from app.services.payment import (
    get_invoice, get_invoice_by_number, get_invoices, create_invoice,
    update_invoice, update_invoice_status, update_invoice_notes, delete_invoice,
    convert_quote_to_invoice, check_overdue_invoices, get_invoice_statistics,
    get_invoice_history, count_invoice_history
)
from app.services.settings import get_general_settings
from app.services.email import send_invoice_email
from app.utils.security import get_current_user

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[InvoiceStatus] = Query(None, description="Filter by invoice status"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    search: Optional[str] = Query(None, description="Search by invoice number or customer name"),
    from_date: Optional[date] = Query(None, description="Filter by issue date from"),
    to_date: Optional[date] = Query(None, description="Filter by issue date to"),
    overdue_only: bool = Query(False, description="Filter only overdue invoices"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of invoices with optional filtering and search
    """
    invoices = get_invoices(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        status=status,
        customer_id=customer_id,
        search=search,
        from_date=from_date,
        to_date=to_date,
        overdue_only=overdue_only
    )
    
    # Get total count for pagination
    total_invoices = len(get_invoices(
        db=db,
        current_user=current_user,
        skip=0,
        limit=10000,
        status=status,
        customer_id=customer_id,
        search=search,
        from_date=from_date,
        to_date=to_date,
        overdue_only=overdue_only
    ))
    
    return {
        "invoices": invoices,
        "total": total_invoices,
        "skip": skip,
        "limit": limit
    }


@router.get("/statistics", response_model=dict)
async def get_invoice_statistics_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get invoice statistics for dashboard
    """
    stats = get_invoice_statistics(db=db, user_id=current_user.id)
    return stats


@router.get("/overdue", response_model=OverdueInvoicesResponse)
async def get_overdue_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overdue invoices
    """
    invoices = get_invoices(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        overdue_only=True
    )
    
    return {
        "overdue_invoices": invoices,
        "count": len(invoices)
    }


@router.post("/check-overdue", response_model=OverdueInvoicesCheckResponse)
async def check_overdue_invoices_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check for overdue invoices and update their status
    """
    overdue_invoices = check_overdue_invoices(db=db)
    
    # Filter to only return invoices belonging to current user
    user_overdue_invoices = [i for i in overdue_invoices if i.user_id == current_user.id]
    
    return {
        "overdue_count": len(user_overdue_invoices),
        "overdue_invoices": user_overdue_invoices
    }


@router.post("/from-quote", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice_from_quote(
    conversion_request: QuoteToInvoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Convert a quote to an invoice
    """
    try:
        invoice = convert_quote_to_invoice(
            db=db,
            conversion_request=conversion_request,
            user_id=current_user.id
        )
        return invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice_endpoint(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new invoice
    """
    try:
        db_invoice = create_invoice(
            db=db,
            invoice=invoice,
            current_user=current_user
        )
        return db_invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/number/{invoice_number}", response_model=InvoiceResponse)
async def get_invoice_by_number_endpoint(
    invoice_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an invoice by invoice number
    """
    invoice = get_invoice_by_number(
        db=db,
        invoice_number=invoice_number,
        user_id=current_user.id
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice_endpoint(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific invoice by ID
    """
    invoice = get_invoice(db=db, invoice_id=invoice_id, current_user=current_user)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice_endpoint(
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an invoice
    """
    try:
        updated_invoice = update_invoice(
            db=db,
            invoice_id=invoice_id,
            invoice_update=invoice_update,
            user_id=current_user.id
        )
        return updated_invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status_endpoint(
    invoice_id: int,
    status_update: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update invoice status with workflow validation
    """
    try:
        updated_invoice = update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{invoice_id}/notes", response_model=InvoiceResponse)
async def update_invoice_notes_endpoint(
    invoice_id: int,
    notes_update: InvoiceNotesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update invoice notes only
    """
    try:
        updated_invoice = update_invoice_notes(
            db=db,
            invoice_id=invoice_id,
            notes_update=notes_update,
            user_id=current_user.id
        )
        return updated_invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice_endpoint(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an invoice
    """
    success = delete_invoice(
        db=db,
        invoice_id=invoice_id,
        user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )


# Invoice Workflow Actions
@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send an invoice (change status from draft to sent and email to customer)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.sent)
    try:
        # First update the invoice status
        updated_invoice = update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status_update=status_update,
            user_id=current_user.id
        )
        
        # Then attempt to send email to customer
        try:
            # Check if customer has email
            if updated_invoice.customer and updated_invoice.customer.email:
                # Get company information from settings
                settings = get_general_settings(db)
                company_info = {
                    "name": settings.company_name if settings else "Your Company",
                    "email": settings.company_email if settings else current_user.email
                }
                
                # Prepare invoice data for email
                invoice_data = {
                    "invoice_number": updated_invoice.invoice_number,
                    "total": float(updated_invoice.total),
                    "amount_due": float(updated_invoice.amount_due),
                    "status": updated_invoice.status,
                    "issue_date": updated_invoice.issue_date,
                    "due_date": updated_invoice.due_date,
                    "formatted_issue_date": updated_invoice.issue_date.strftime("%B %d, %Y"),
                    "formatted_due_date": updated_invoice.due_date.strftime("%B %d, %Y"),
                    "payment_terms": updated_invoice.payment_terms,
                    "notes": updated_invoice.notes,
                    "items": []
                }
                
                # Add invoice items if available
                if updated_invoice.items:
                    for item in updated_invoice.items:
                        invoice_data["items"].append({
                            "package": {
                                "name": item.package.name if item.package else "Service"
                            },
                            "unit_price": float(item.unit_price),
                            "discount": float(item.discount),
                            "line_total": float(item.line_total)
                        })
                
                # Send the invoice email
                email_sent = await send_invoice_email(
                    customer_email=updated_invoice.customer.email,
                    customer_name=updated_invoice.customer.name,
                    invoice_data=invoice_data,
                    company_info=company_info
                )
                
                if email_sent:
                    logger.info(f"Invoice #{updated_invoice.invoice_number} successfully sent via email to {updated_invoice.customer.email}")
                else:
                    logger.warning(f"Invoice #{updated_invoice.invoice_number} status updated but email sending failed")
            else:
                logger.warning(f"Invoice #{updated_invoice.invoice_number} status updated but customer has no email address")
                
        except Exception as email_error:
            # Log email error but don't fail the entire operation since status was updated successfully
            logger.error(f"Failed to send invoice email for invoice #{updated_invoice.invoice_number}: {str(email_error)}")
        
        return updated_invoice
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark an invoice as paid
    """
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.paid)
    try:
        updated_invoice = update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an invoice
    """
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.cancelled)
    try:
        updated_invoice = update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{invoice_id}/reopen", response_model=InvoiceResponse)
async def reopen_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reopen a cancelled invoice (change status back to draft)
    """
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.draft)
    try:
        updated_invoice = update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{invoice_id}/preview", response_model=InvoicePreviewResponse)
async def preview_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get invoice preview data for PDF generation or display
    """
    invoice = get_invoice(db=db, invoice_id=invoice_id, current_user=current_user)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Calculate payment summary
    from decimal import Decimal
    total_paid = sum(
        payment.amount for payment in invoice.payments 
        if payment.status == 'completed'
    ) if invoice.payments else Decimal('0.00')
    
    balance_due = invoice.total - total_paid
    
    # Get company information from settings
    settings = get_general_settings(db)
    company_name = settings.company_name if settings else "Your Company"
    company_email = settings.company_email if settings else current_user.email
    
    # Return formatted data for preview/PDF generation
    return {
        "invoice": invoice,
        "company_info": {
            "name": company_name,
            "email": company_email,
            # Add more company details as needed
        },
        "payment_summary": {
            "total_amount": invoice.total,
            "total_paid": total_paid,
            "balance_due": balance_due,
            "is_paid": balance_due <= Decimal('0.00')
        },
        "formatted_issue_date": invoice.issue_date.strftime("%B %d, %Y"),
        "formatted_due_date": invoice.due_date.strftime("%B %d, %Y"),
        "status_display": invoice.status.title(),
        "is_overdue": invoice.due_date < date.today() and invoice.status in ['sent', 'overdue']
    }


@router.get("/{invoice_id}/pdf", response_model=InvoicePreviewResponse)
async def get_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get invoice PDF data - alias for preview endpoint
    """
    return await preview_invoice(invoice_id, db, current_user)


@router.get("/{invoice_id}/history", response_model=InvoiceHistoryListResponse)
async def get_invoice_history_endpoint(
    invoice_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    event_category: Optional[InvoiceHistoryEventCategory] = Query(None, description="Filter by event category"),
    from_date: Optional[date] = Query(None, description="Filter by date from"),
    to_date: Optional[date] = Query(None, description="Filter by date to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get invoice history with optional filtering and pagination
    """
    # First verify the invoice exists and user has access
    invoice = get_invoice(db=db, invoice_id=invoice_id, current_user=current_user)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Get history events
    history_events = get_invoice_history(
        db=db,
        invoice_id=invoice_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        event_category=event_category.value if event_category else None,
        from_date=from_date,
        to_date=to_date
    )
    
    # Get total count for pagination
    total_events = count_invoice_history(
        db=db,
        invoice_id=invoice_id,
        current_user=current_user,
        event_category=event_category.value if event_category else None,
        from_date=from_date,
        to_date=to_date
    )
    
    # Format history events for response
    formatted_history = []
    for event in history_events:
        formatted_history.append({
            "id": event.id,
            "event_type": event.event_type,
            "event_category": event.event_category,
            "description": event.description,
            "user_name": event.user.full_name if event.user and event.user.full_name else event.user.username if event.user else "Unknown User",
            "user_email": event.user.email if event.user else None,
            "metadata": event.event_metadata,
            "created_at": event.created_at,
            "formatted_date": event.created_at.strftime("%B %d, %Y at %I:%M %p")
        })
    
    return {
        "invoice_id": invoice_id,
        "invoice_number": invoice.invoice_number,
        "history": formatted_history,
        "total_events": total_events,
        "skip": skip,
        "limit": limit
    }