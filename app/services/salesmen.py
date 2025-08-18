"""
Salesmen services for the XerpeX ERP System
"""
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.salesmen import Salesmen
from app.schemas.salesmen import SalesmenCreate, SalesmenUpdate
def get_salesman(db: Session, salesman_id: int) -> Optional[Salesmen]:
    """
    Get a salesman by ID
    
    Args:
        db: Database session
        salesman_id: Salesman ID
        
    Returns:
        Salesmen: Salesman or None
    """
    return db.query(Salesmen).filter(Salesmen.id == salesman_id).first()


def get_salesman_by_email(db: Session, email: str) -> Optional[Salesmen]:
    """
    Get a salesman by email
    
    Args:
        db: Database session
        email: Salesman email
        
    Returns:
        Salesmen: Salesman or None
    """
    return db.query(Salesmen).filter(Salesmen.email == email).first()


def get_salesmen(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    is_active: Optional[bool] = None
) -> List[Salesmen]:
    """
    Get salesmen with optional filtering
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        is_active: Filter by active status
        
    Returns:
        List[Salesmen]: List of salesmen
    """
    query = db.query(Salesmen)
    
    if is_active is not None:
        query = query.filter(Salesmen.is_active == is_active)
    
    return query.offset(skip).limit(limit).all()


def create_salesman(db: Session, salesman: SalesmenCreate) -> Salesmen:
    """
    Create a new salesman
    
    Args:
        db: Database session
        salesman: Salesman data
        
    Returns:
        Salesmen: Created salesman
        
    Raises:
        HTTPException: If salesman already exists
    """
    # Check if salesman already exists
    db_salesman = get_salesman_by_email(db, salesman.email)
    
    if db_salesman:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new salesman
    db_salesman = Salesmen(
        first_name=salesman.first_name,
        last_name=salesman.last_name,
        email=salesman.email,
        phone_number=salesman.phone_number,
        is_active=salesman.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_salesman)
    db.commit()
    db.refresh(db_salesman)
    
    return db_salesman


def update_salesman(db: Session, salesman_id: int, salesman_update: SalesmenUpdate) -> Salesmen:
    """
    Update a salesman
    
    Args:
        db: Database session
        salesman_id: Salesman ID
        salesman_update: Salesman update data
        
    Returns:
        Salesmen: Updated salesman
        
    Raises:
        HTTPException: If salesman not found or email already taken
    """
    db_salesman = get_salesman(db, salesman_id)
    if not db_salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )
    
    # Check if email is being updated and is already taken
    if salesman_update.email and salesman_update.email != db_salesman.email:
        existing_salesman = get_salesman_by_email(db, salesman_update.email)
        if existing_salesman:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Update salesman fields
    update_data = salesman_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_salesman, key, value)
    
    db_salesman.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_salesman)
    
    return db_salesman


def delete_salesman(db: Session, salesman_id: int) -> bool:
    """
    Delete a salesman
    
    Args:
        db: Database session
        salesman_id: Salesman ID
        
    Returns:
        bool: True if salesman was deleted
        
    Raises:
        HTTPException: If salesman not found or is default salesman
    """
    db_salesman = get_salesman(db, salesman_id)
    if not db_salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )
    
    # Prevent deletion of default salesman (ID = 1)
    if salesman_id == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default salesman"
        )
    
    # Check if salesman has active surveys
    if db_salesman.surveys:
        # Instead of preventing deletion, we'll set surveys to default salesman
        for survey in db_salesman.surveys:
            survey.salesmen_id = 1
    
    db.delete(db_salesman)
    db.commit()
    
    return True


def get_active_salesmen_for_dropdown(db: Session) -> List[Salesmen]:
    """
    Get active salesmen for dropdown/select options
    
    Args:
        db: Database session
        
    Returns:
        List[Salesmen]: List of active salesmen
    """
    return db.query(Salesmen).filter(Salesmen.is_active == True).all()