"""
Tax services for the XerpeX ERP System
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.tax import Tax
from app.models.user import User
from app.schemas.tax import TaxCreate, TaxUpdate
from app.utils.security import get_user_filter_condition, should_apply_user_isolation


def get_tax(db: Session, tax_id: int, current_user: User) -> Optional[Tax]:
    """
    Get a tax by ID with role-based user isolation
    
    Args:
        db: Database session
        tax_id: Tax ID
        current_user: Current user (for role-based access control)
        
    Returns:
        Tax: Tax or None
    """
    query = db.query(Tax).filter(Tax.id == tax_id)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Tax.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.first()


def get_taxes(
    db: Session, 
    current_user: User,
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = False
) -> List[Tax]:
    """
    Get taxes with optional filtering (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Filter only active taxes
        
    Returns:
        List[Tax]: List of taxes
    """
    query = db.query(Tax)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Tax.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    if active_only:
        # For now, we don't have an is_active field, so return all
        # This can be extended when we add tax activation/deactivation
        pass
    
    return query.offset(skip).limit(limit).all()


def create_tax(db: Session, tax: TaxCreate, current_user: User) -> Tax:
    """
    Create a new tax
    
    Args:
        db: Database session
        tax: Tax data
        current_user: Current user (for role-based access control)
        
    Returns:
        Tax: Created tax
    """
    # Check if tax with same name already exists
    query = db.query(Tax).filter(Tax.name == tax.name)
    
    # Apply user isolation for name uniqueness check
    user_filter = get_user_filter_condition(current_user, Tax.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    existing_tax = query.first()
    if existing_tax:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax with this name already exists"
        )
    
    # Validate percentage
    if tax.percentage < 0 or tax.percentage > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax percentage must be between 0 and 100"
        )
    
    db_tax = Tax(
        user_id=current_user.id,
        name=tax.name,
        percentage=tax.percentage,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_tax)
    db.commit()
    db.refresh(db_tax)
    
    return db_tax


def update_tax(
    db: Session, 
    tax_id: int, 
    tax_update: TaxUpdate, 
    current_user: User
) -> Tax:
    """
    Update a tax
    
    Args:
        db: Database session
        tax_id: Tax ID
        tax_update: Tax update data
        current_user: Current user (for role-based access control)
        
    Returns:
        Tax: Updated tax
        
    Raises:
        HTTPException: If tax not found or name conflict
    """
    db_tax = get_tax(db, tax_id, current_user)
    if not db_tax:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax not found"
        )
    
    # Check for name conflicts if name is being updated
    if tax_update.name and tax_update.name != db_tax.name:
        query = db.query(Tax).filter(
            and_(
                Tax.name == tax_update.name,
                Tax.id != tax_id
            )
        )
        
        # Apply user isolation for name uniqueness check
        user_filter = get_user_filter_condition(current_user, Tax.user_id)
        if user_filter is not True:  # True means no filter (admin/finance)
            query = query.filter(user_filter)
        
        existing_tax = query.first()
        if existing_tax:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tax with this name already exists"
            )
    
    # Validate percentage if being updated
    if tax_update.percentage is not None:
        if tax_update.percentage < 0 or tax_update.percentage > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tax percentage must be between 0 and 100"
            )
    
    # Update tax fields
    update_data = tax_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_tax, key, value)
    
    db_tax.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_tax)
    
    return db_tax


def delete_tax(db: Session, tax_id: int, current_user: User) -> bool:
    """
    Delete a tax
    
    Args:
        db: Database session
        tax_id: Tax ID
        current_user: Current user (for role-based access control)
        
    Returns:
        bool: True if tax was deleted
        
    Raises:
        HTTPException: If tax not found or has related records
    """
    db_tax = get_tax(db, tax_id, current_user)
    if not db_tax:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax not found"
        )
    
    # Note: We should check if tax is used in any quotes or invoices
    # This would require checking related records
    # For now, we'll allow deletion
    
    db.delete(db_tax)
    db.commit()
    
    return True


def calculate_total_with_taxes(subtotal: Decimal, taxes: List[Tax]) -> Dict[str, Any]:
    """
    Calculate total with taxes applied
    
    Args:
        subtotal: Subtotal amount
        taxes: List of taxes to apply
        
    Returns:
        Dict: Dictionary with subtotal, tax_total, total, and tax_breakdown
    """
    tax_total = Decimal('0.00')
    tax_breakdown = []
    
    for tax in taxes:
        tax_amount = subtotal * (tax.percentage / 100)
        tax_total += tax_amount
        
        tax_breakdown.append({
            'name': tax.name,
            'percentage': tax.percentage,
            'amount': tax_amount
        })
    
    return {
        'subtotal': subtotal,
        'tax_total': tax_total,
        'total': subtotal + tax_total,
        'tax_breakdown': tax_breakdown
    }


def calculate_taxes_for_amount(db: Session, amount: Decimal, tax_ids: List[int], current_user: User) -> Dict[str, Any]:
    """
    Calculate taxes for a given amount
    
    Args:
        db: Database session
        amount: Amount to calculate taxes for
        tax_ids: List of tax IDs to apply
        current_user: Current user (for role-based access control)
        
    Returns:
        Dict: Dictionary with calculation results
    """
    # Get taxes with role-based filtering
    query = db.query(Tax).filter(Tax.id.in_(tax_ids))
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Tax.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    taxes = query.all()
    
    if len(taxes) != len(tax_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more taxes not found"
        )
    
    return calculate_total_with_taxes(amount, taxes)


def get_tax_count(db: Session, current_user: User) -> int:
    """
    Get total count of taxes (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        
    Returns:
        int: Total count of taxes
    """
    query = db.query(Tax)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Tax.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.count()


def get_active_taxes(db: Session, current_user: User) -> List[Tax]:
    """
    Get all active taxes (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        
    Returns:
        List[Tax]: List of all taxes accessible to the user
    """
    query = db.query(Tax)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Tax.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.order_by(Tax.name).all()