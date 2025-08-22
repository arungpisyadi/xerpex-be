"""
Customer API controllers for the XerpeX ERP System
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, Customer
)
from app.services.customer import (
    get_customer, get_customers, create_customer, update_customer,
    delete_customer, get_customer_count, search_customers_by_name
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/")
async def list_customers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    active_only: bool = Query(True, description="Filter only active customers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of customers with optional filtering and search
    """
    customers = get_customers(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        search=search
    )
    
    # Get total count for pagination
    total_customers = get_customer_count(db=db, current_user=current_user)
    
    return {
        "customers": customers,
        "total": total_customers,
        "skip": skip,
        "limit": limit
    }


@router.get("/search", response_model=List[Customer])
async def search_customers_endpoint(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search customers by name, email, or phone
    """
    customers = search_customers_by_name(
        db=db,
        name=query,
        current_user=current_user,
        limit=limit
    )
    
    return customers


@router.get("/statistics")
async def get_customer_statistics_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get customer statistics for dashboard
    """
    count = get_customer_count(db=db, current_user=current_user)
    return {"total_customers": count}


@router.post("/", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer_endpoint(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new customer
    """
    try:
        db_customer = create_customer(
            db=db,
            customer=customer,
            current_user=current_user
        )
        return db_customer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{customer_id}", response_model=Customer)
async def get_customer_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific customer by ID
    """
    customer = get_customer(db=db, customer_id=customer_id, current_user=current_user)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer


@router.put("/{customer_id}", response_model=Customer)
async def update_customer_endpoint(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a customer
    """
    try:
        updated_customer = update_customer(
            db=db,
            customer_id=customer_id,
            customer_update=customer_update,
            current_user=current_user
        )
        return updated_customer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a customer
    """
    success = delete_customer(
        db=db,
        customer_id=customer_id,
        current_user=current_user
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )


@router.post("/{customer_id}/activate", response_model=Customer)
async def activate_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activate a customer
    """
    customer_update = CustomerUpdate(is_active=True)
    try:
        updated_customer = update_customer(
            db=db,
            customer_id=customer_id,
            customer_update=customer_update,
            current_user=current_user
        )
        return updated_customer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{customer_id}/deactivate", response_model=Customer)
async def deactivate_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deactivate a customer
    """
    customer_update = CustomerUpdate(is_active=False)
    try:
        updated_customer = update_customer(
            db=db,
            customer_id=customer_id,
            customer_update=customer_update,
            current_user=current_user
        )
        return updated_customer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )