"""
Tax API controllers for the XerpeX ERP System
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.tax import (
    TaxCreate, TaxUpdate, Tax, TaxListResponse,
    TaxStatisticsResponse, TaxCalculationResponse
)
from app.services.tax import (
    get_tax, get_taxes, create_tax, update_tax, delete_tax,
    calculate_total_with_taxes, get_tax_count
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/taxes", tags=["taxes"])


@router.get("/", response_model=TaxListResponse)
async def list_taxes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    active_only: bool = Query(True, description="Filter only active taxes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of taxes with optional filtering
    """
    taxes = get_taxes(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        active_only=active_only
    )
    
    # Get total count for pagination
    total_taxes = get_tax_count(db=db, current_user=current_user)
    
    return {
        "taxes": taxes,
        "total": total_taxes,
        "skip": skip,
        "limit": limit
    }


@router.get("/statistics", response_model=TaxStatisticsResponse)
async def get_tax_statistics_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tax statistics for dashboard
    """
    count = get_tax_count(db=db, current_user=current_user)
    return {"total_taxes": count}


@router.post("/calculate", response_model=TaxCalculationResponse)
async def calculate_taxes(
    calculation_request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate taxes for a given amount
    """
    # Get taxes
    taxes = []
    for tax_id in calculation_request.get("tax_ids", []):
        tax = get_tax(db=db, tax_id=tax_id, current_user=current_user)
        if not tax:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tax with ID {tax_id} not found"
            )
        taxes.append(tax)
    
    # Calculate totals
    result = calculate_total_with_taxes(calculation_request.get("amount", 0), taxes)
    
    return result


@router.post("/", response_model=Tax, status_code=status.HTTP_201_CREATED)
async def create_tax_endpoint(
    tax: TaxCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new tax
    """
    try:
        db_tax = create_tax(
            db=db,
            tax=tax,
            current_user=current_user
        )
        return db_tax
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{tax_id}", response_model=Tax)
async def get_tax_endpoint(
    tax_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific tax by ID
    """
    tax = get_tax(db=db, tax_id=tax_id, current_user=current_user)
    if not tax:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax not found"
        )
    return tax


@router.put("/{tax_id}", response_model=Tax)
async def update_tax_endpoint(
    tax_id: int,
    tax_update: TaxUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a tax
    """
    try:
        updated_tax = update_tax(
            db=db,
            tax_id=tax_id,
            tax_update=tax_update,
            current_user=current_user
        )
        return updated_tax
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_endpoint(
    tax_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a tax
    """
    success = delete_tax(
        db=db,
        tax_id=tax_id,
        current_user=current_user
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax not found"
        )


@router.post("/{tax_id}/activate", response_model=Tax)
async def activate_tax(
    tax_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activate a tax
    """
    tax_update = TaxUpdate(is_active=True)
    try:
        updated_tax = update_tax(
            db=db,
            tax_id=tax_id,
            tax_update=tax_update,
            current_user=current_user
        )
        return updated_tax
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{tax_id}/deactivate", response_model=Tax)
async def deactivate_tax(
    tax_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deactivate a tax
    """
    tax_update = TaxUpdate(is_active=False)
    try:
        updated_tax = update_tax(
            db=db,
            tax_id=tax_id,
            tax_update=tax_update,
            current_user=current_user
        )
        return updated_tax
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )