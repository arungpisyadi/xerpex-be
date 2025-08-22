"""
Quote API controllers for the XerpeX ERP System
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.quote import (
    QuoteCreate, QuoteUpdate, QuoteStatusUpdate, Quote,
    QuoteStatus, QuoteConversionRequest, QuoteListResponse,
    QuoteCalculationResponse, ExpiredQuotesResponse,
    QuoteConversionResponse, QuotePreviewResponse
)
from app.services.quote import (
    get_quote, get_quotes, create_quote, update_quote, update_quote_status,
    delete_quote, calculate_quote_totals, get_quote_statistics,
    check_expired_quotes
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("/", response_model=QuoteListResponse)
async def list_quotes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[QuoteStatus] = Query(None, description="Filter by quote status"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    search: Optional[str] = Query(None, description="Search by quote number or customer name"),
    from_date: Optional[date] = Query(None, description="Filter by issue date from"),
    to_date: Optional[date] = Query(None, description="Filter by issue date to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of quotes with optional filtering and search
    """
    quotes = get_quotes(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        status=status,
        customer_id=customer_id,
        search=search,
        from_date=from_date,
        to_date=to_date
    )
    
    # Get total count for pagination
    total_quotes = len(get_quotes(
        db=db,
        current_user=current_user,
        skip=0,
        limit=10000,
        status=status,
        customer_id=customer_id,
        search=search,
        from_date=from_date,
        to_date=to_date
    ))
    
    return {
        "quotes": quotes,
        "total": total_quotes,
        "skip": skip,
        "limit": limit
    }


@router.get("/statistics", response_model=dict)
async def get_quote_statistics_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get quote statistics for dashboard
    """
    stats = get_quote_statistics(db=db, user_id=current_user.id)
    return stats


@router.post("/calculate-totals", response_model=QuoteCalculationResponse)
async def calculate_quote_totals_endpoint(
    items: List[dict],
    tax_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate quote totals including taxes
    """
    from app.schemas.quote import QuoteItemCreate
    
    # Convert dict items to QuoteItemCreate objects
    quote_items = [QuoteItemCreate(**item) for item in items]
    
    result = calculate_quote_totals(
        db=db,
        items=quote_items,
        user_id=current_user.id,
        tax_ids=tax_ids
    )
    
    return result


@router.post("/check-expired", response_model=ExpiredQuotesResponse)
async def check_expired_quotes_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check for expired quotes and update their status
    """
    expired_quotes = check_expired_quotes(db=db)
    
    # Filter to only return quotes belonging to current user
    user_expired_quotes = [q for q in expired_quotes if q.user_id == current_user.id]
    
    return {
        "expired_count": len(user_expired_quotes),
        "expired_quotes": user_expired_quotes
    }


@router.post("/", response_model=Quote, status_code=status.HTTP_201_CREATED)
async def create_quote_endpoint(
    quote: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new quote
    """
    try:
        db_quote = create_quote(
            db=db,
            quote=quote,
            current_user=current_user
        )
        return db_quote
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{quote_id}", response_model=Quote)
async def get_quote_endpoint(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific quote by ID
    """
    quote = get_quote(db=db, quote_id=quote_id, current_user=current_user)
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    return quote


@router.put("/{quote_id}", response_model=Quote)
async def update_quote_endpoint(
    quote_id: int,
    quote_update: QuoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a quote
    """
    try:
        updated_quote = update_quote(
            db=db,
            quote_id=quote_id,
            quote_update=quote_update,
            user_id=current_user.id
        )
        return updated_quote
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{quote_id}/status", response_model=Quote)
async def update_quote_status_endpoint(
    quote_id: int,
    status_update: QuoteStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update quote status with workflow validation
    """
    try:
        updated_quote = update_quote_status(
            db=db,
            quote_id=quote_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_quote
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote_endpoint(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a quote
    """
    success = delete_quote(
        db=db,
        quote_id=quote_id,
        user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )


# Quote Workflow Actions
@router.post("/{quote_id}/send", response_model=Quote)
async def send_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a quote (change status from draft to sent)
    """
    status_update = QuoteStatusUpdate(status=QuoteStatus.sent)
    try:
        updated_quote = update_quote_status(
            db=db,
            quote_id=quote_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_quote
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{quote_id}/accept", response_model=Quote)
async def accept_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept a quote (change status to accepted)
    """
    status_update = QuoteStatusUpdate(status=QuoteStatus.accepted)
    try:
        updated_quote = update_quote_status(
            db=db,
            quote_id=quote_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_quote
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{quote_id}/decline", response_model=Quote)
async def decline_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Decline a quote (change status to declined)
    """
    status_update = QuoteStatusUpdate(status=QuoteStatus.declined)
    try:
        updated_quote = update_quote_status(
            db=db,
            quote_id=quote_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_quote
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{quote_id}/reopen", response_model=Quote)
async def reopen_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reopen a declined or expired quote (change status back to draft)
    """
    status_update = QuoteStatusUpdate(status=QuoteStatus.draft)
    try:
        updated_quote = update_quote_status(
            db=db,
            quote_id=quote_id,
            status_update=status_update,
            user_id=current_user.id
        )
        return updated_quote
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{quote_id}/convert-to-invoice", response_model=QuoteConversionResponse)
async def convert_quote_to_invoice(
    quote_id: int,
    conversion_request: QuoteConversionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Convert a quote to an invoice
    """
    from app.schemas.payment import QuoteToInvoiceRequest
    from app.services.payment import convert_quote_to_invoice
    
    # Create conversion request
    invoice_request = QuoteToInvoiceRequest(
        quote_id=quote_id,
        issue_date=conversion_request.issue_date,
        due_date=conversion_request.due_date,
        notes=conversion_request.notes
    )
    
    try:
        invoice = convert_quote_to_invoice(
            db=db,
            conversion_request=invoice_request,
            user_id=current_user.id
        )
        return {
            "message": "Quote successfully converted to invoice",
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{quote_id}/preview", response_model=QuotePreviewResponse)
async def preview_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get quote preview data for PDF generation or display
    """
    quote = get_quote(db=db, quote_id=quote_id, current_user=current_user)
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Return formatted data for preview/PDF generation
    return {
        "quote": quote,
        "company_info": {
            "name": current_user.company_name or "Your Company",
            "email": current_user.email,
            # Add more company details as needed
        },
        "formatted_date": quote.issue_date.strftime("%B %d, %Y"),
        "formatted_expiry": quote.expiry_date.strftime("%B %d, %Y") if quote.expiry_date else None,
        "status_display": quote.status.title()
    }