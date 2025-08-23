"""
Booking controller for the XerpeX ERP System
"""
from datetime import date
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingResponse, BookingDetailResponse,
    BookingStatusUpdate, BookingVillaCreate, BookingVillaResponse,
    BookingPackageCreate, BookingPackageResponse,
    BookingAddonCreate, BookingAddonResponse
)
from app.services.booking import (
    get_booking, get_bookings, create_booking, update_booking,
    update_booking_status, delete_booking, get_booking_details,
    add_booking_villa, remove_booking_villa,
    add_booking_package, remove_booking_package,
    add_booking_addon, remove_booking_addon
)
from app.utils.security import get_current_active_user, get_current_admin_user


router = APIRouter(
    prefix="/bookings",
    tags=["bookings"],
    dependencies=[Depends(get_current_active_user)]
)


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking_endpoint(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Create a new booking
    """
    return create_booking(db, booking, current_user.id)


@router.get("", response_model=List[BookingResponse])
def read_bookings(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    guest_name: Optional[str] = None,
    check_in_from: Optional[date] = None,
    check_in_to: Optional[date] = None,
    villa_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get all bookings with optional filtering
    """
    return get_bookings(
        db, 
        skip=skip, 
        limit=limit,
        status=status,
        guest_name=guest_name,
        check_in_from=check_in_from,
        check_in_to=check_in_to,
        villa_id=villa_id
    )


@router.get("/{booking_id}", response_model=BookingResponse)
def read_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get a booking by ID
    """
    db_booking = get_booking(db, booking_id)
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return db_booking


@router.get("/{booking_id}/details", response_model=BookingDetailResponse)
def read_booking_details(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get detailed booking information including financial details
    """
    return get_booking_details(db, booking_id)


@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking_endpoint(
    booking_id: int,
    booking_update: BookingUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Update a booking
    """
    return update_booking(db, booking_id, booking_update)


@router.patch("/{booking_id}/status", response_model=BookingResponse)
def update_booking_status_endpoint(
    booking_id: int,
    status_update: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Update a booking status
    """
    return update_booking_status(db, booking_id, status_update)


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Delete a booking (admin only)
    """
    delete_booking(db, booking_id)
    return {"detail": "Booking deleted successfully"}


# Villa management within bookings
@router.post("/{booking_id}/villas", response_model=BookingVillaResponse)
def add_villa_to_booking(
    booking_id: int,
    villa_data: BookingVillaCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Add a villa to a booking
    """
    return add_booking_villa(db, booking_id, villa_data)


@router.delete("/{booking_id}/villas/{villa_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_villa_from_booking(
    booking_id: int,
    villa_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Remove a villa from a booking
    """
    remove_booking_villa(db, booking_id, villa_id)
    return {"detail": "Villa removed from booking successfully"}


# Package management within bookings
@router.post("/{booking_id}/packages", response_model=BookingPackageResponse)
def add_package_to_booking(
    booking_id: int,
    package_data: BookingPackageCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Add a package to a booking
    """
    return add_booking_package(db, booking_id, package_data)


@router.delete("/{booking_id}/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_package_from_booking(
    booking_id: int,
    package_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Remove a package from a booking
    """
    remove_booking_package(db, booking_id, package_id)
    return {"detail": "Package removed from booking successfully"}


# Addon management within bookings
@router.post("/{booking_id}/addons", response_model=BookingAddonResponse)
def add_addon_to_booking(
    booking_id: int,
    addon_data: BookingAddonCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Add an addon to a booking
    """
    return add_booking_addon(db, booking_id, addon_data)


@router.delete("/{booking_id}/addons/{addon_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_addon_from_booking(
    booking_id: int,
    addon_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Remove an addon from a booking
    """
    remove_booking_addon(db, booking_id, addon_id)
    return {"detail": "Addon removed from booking successfully"}