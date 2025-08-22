"""
Customer services for the XerpeX ERP System
"""
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.utils.security import get_user_filter_condition, should_apply_user_isolation


def get_customer(db: Session, customer_id: int, current_user: User) -> Optional[Customer]:
    """
    Get a customer by ID with role-based user isolation
    
    Args:
        db: Database session
        customer_id: Customer ID
        current_user: Current user (for role-based access control)
        
    Returns:
        Customer: Customer or None
    """
    query = db.query(Customer).filter(Customer.id == customer_id)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Customer.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.first()


def get_customers(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> List[Customer]:
    """
    Get customers with optional filtering and search (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search by name or email (partial match)
        
    Returns:
        List[Customer]: List of customers
    """
    query = db.query(Customer)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Customer.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%")
            )
        )
    
    return query.offset(skip).limit(limit).all()


def create_customer(db: Session, customer: CustomerCreate, current_user: User) -> Customer:
    """
    Create a new customer
    
    Args:
        db: Database session
        customer: Customer data
        current_user: Current user (for role-based access control)
        
    Returns:
        Customer: Created customer
    """
    # Check if customer with same email already exists
    if customer.email:
        query = db.query(Customer).filter(Customer.email == customer.email)
        
        # Apply user isolation for email uniqueness check
        user_filter = get_user_filter_condition(current_user, Customer.user_id)
        if user_filter is not True:  # True means no filter (admin/finance)
            query = query.filter(user_filter)
        
        existing_customer = query.first()
        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer with this email already exists"
            )
    
    db_customer = Customer(
        user_id=current_user.id,
        name=customer.name,
        email=customer.email,
        billing_address=customer.billing_address,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    return db_customer


def update_customer(
    db: Session,
    customer_id: int,
    customer_update: CustomerUpdate,
    current_user: User
) -> Customer:
    """
    Update a customer
    
    Args:
        db: Database session
        customer_id: Customer ID
        customer_update: Customer update data
        current_user: Current user (for role-based access control)
        
    Returns:
        Customer: Updated customer
        
    Raises:
        HTTPException: If customer not found or email conflict
    """
    db_customer = get_customer(db, customer_id, current_user)
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Check for email conflicts if email is being updated
    if customer_update.email and customer_update.email != db_customer.email:
        query = db.query(Customer).filter(
            and_(
                Customer.email == customer_update.email,
                Customer.id != customer_id
            )
        )
        
        # Apply user isolation for email uniqueness check
        user_filter = get_user_filter_condition(current_user, Customer.user_id)
        if user_filter is not True:  # True means no filter (admin/finance)
            query = query.filter(user_filter)
        
        existing_customer = query.first()
        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer with this email already exists"
            )
    
    # Update customer fields
    update_data = customer_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_customer, key, value)
    
    db_customer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_customer)
    
    return db_customer


def delete_customer(db: Session, customer_id: int, current_user: User) -> bool:
    """
    Delete a customer
    
    Args:
        db: Database session
        customer_id: Customer ID
        current_user: Current user (for role-based access control)
        
    Returns:
        bool: True if customer was deleted
        
    Raises:
        HTTPException: If customer not found or has related records
    """
    db_customer = get_customer(db, customer_id, current_user)
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Check if customer has related quotes or invoices
    if db_customer.quotes or db_customer.invoices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete customer with existing quotes or invoices"
        )
    
    db.delete(db_customer)
    db.commit()
    
    return True


def get_customer_count(db: Session, current_user: User) -> int:
    """
    Get total count of customers (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        
    Returns:
        int: Total count of customers
    """
    query = db.query(Customer)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Customer.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.count()


def search_customers_by_name(db: Session, name: str, current_user: User, limit: int = 10) -> List[Customer]:
    """
    Search customers by name for autocomplete functionality
    
    Args:
        db: Database session
        name: Name to search for
        current_user: Current user (for role-based access control)
        limit: Maximum number of results
        
    Returns:
        List[Customer]: List of matching customers
    """
    query = db.query(Customer).filter(Customer.name.ilike(f"%{name}%"))
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Customer.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.limit(limit).all()