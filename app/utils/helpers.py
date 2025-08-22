"""
Helper utilities for the XerpeX ERP System
"""
import random
import string
from datetime import datetime, date
from typing import Optional


def generate_booking_code(prefix: str = "BK") -> str:
    """
    Generate a unique booking code
    
    Args:
        prefix: Booking code prefix
        
    Returns:
        str: Unique booking code
    """
    timestamp = datetime.now().strftime("%y%m%d")
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}{timestamp}{random_chars}"


def generate_invoice_number(prefix: str = "INV") -> str:
    """
    Generate a unique invoice number
    
    Args:
        prefix: Invoice number prefix
        
    Returns:
        str: Unique invoice number
    """
    timestamp = datetime.now().strftime("%y%m%d")
    random_chars = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}{timestamp}{random_chars}"


def generate_quote_number(prefix: str = "QUO") -> str:
    """
    Generate a unique quote number
    
    Args:
        prefix: Quote number prefix
        
    Returns:
        str: Unique quote number
    """
    timestamp = datetime.now().strftime("%y%m%d")
    random_chars = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}{timestamp}{random_chars}"


def is_date_range_available(
    check_in: date,
    check_out: date,
    existing_check_ins: list[date],
    existing_check_outs: list[date]
) -> bool:
    """
    Check if a date range is available
    
    Args:
        check_in: Check-in date
        check_out: Check-out date
        existing_check_ins: List of existing check-in dates
        existing_check_outs: List of existing check-out dates
        
    Returns:
        bool: True if date range is available
    """
    for i in range(len(existing_check_ins)):
        # Check if there's an overlap
        if (check_in < existing_check_outs[i] and check_out > existing_check_ins[i]):
            return False
    return True


def calculate_nights(check_in: date, check_out: date) -> int:
    """
    Calculate the number of nights between check-in and check-out
    
    Args:
        check_in: Check-in date
        check_out: Check-out date
        
    Returns:
        int: Number of nights
    """
    delta = check_out - check_in
    return delta.days


def sanitize_phone_number(phone_number: Optional[str]) -> Optional[str]:
    """
    Sanitize phone number according to Indonesian format
    
    Rules:
    - Replace leading 0 with 62
    - Replace +62 with 62
    - Remove "-" (hyphens)
    - Remove spaces
    
    Args:
        phone_number: Raw phone number string
        
    Returns:
        str: Sanitized phone number or None if input is None/empty
        
    Examples:
        "0812-3456-7890" -> "6281234567890"
        "+62 812 3456 7890" -> "6281234567890"
        "+62-812-345-6789" -> "62812345678"
        "812 345 6789" -> "812345678"
    """
    if not phone_number or not phone_number.strip():
        return None
    
    # Remove all spaces and hyphens
    sanitized = phone_number.replace(" ", "").replace("-", "")
    
    # Replace +62 with 62 (handle country code)
    if sanitized.startswith("+62"):
        sanitized = "62" + sanitized[3:]
    # Replace leading 0 with 62 (Indonesian mobile format)
    elif sanitized.startswith("0"):
        sanitized = "62" + sanitized[1:]
    
    return sanitized