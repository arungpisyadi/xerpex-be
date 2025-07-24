"""
Database models for the XerpeX ERP System
"""
from app.database import Base
from app.models.user import User, UserActivity
from app.models.villa import Villa, VillaAvailability
from app.models.booking import Booking, BookingVilla, BookingPackage, BookingAddon
from app.models.payment import Payment, Invoice, InvoiceItem

# For Alembic to detect all models
__all__ = [
    "Base",
    "User",
    "UserActivity",
    "Villa",
    "VillaAvailability",
    "Booking",
    "BookingVilla",
    "BookingPackage",
    "BookingAddon",
    "Payment",
    "Invoice",
    "InvoiceItem"
]