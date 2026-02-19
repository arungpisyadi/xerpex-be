"""
Report services for the XerpeX ERP System
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import calendar
from collections import defaultdict

from sqlalchemy import func, and_, or_, extract, case, literal
from sqlalchemy.orm import Session, joinedload

from app.models.booking import Booking, BookingVilla
from app.models.payment import Payment, Invoice
from app.models.villa import Villa, VillaAvailability
from app.schemas.report import (
    ReportVillaOccupancyParams, ReportBookingStatusParams, ReportRevenueParams,
    SalesReportParams
)
def get_villa_occupancy_report(db: Session, params: ReportVillaOccupancyParams) -> Dict[str, Any]:
    """
    Generate villa occupancy report
    
    Args:
        db: Database session
        params: Report parameters
        
    Returns:
        Dict[str, Any]: Villa occupancy report
    """
    # Calculate total days in the date range
    delta = params.end_date - params.start_date
    total_days = delta.days + 1
    
    # Query villas
    villa_query = db.query(Villa)
    if params.villa_id:
        villa_query = villa_query.filter(Villa.id == params.villa_id)
    
    villas = villa_query.all()
    
    # Initialize result
    result = {
        "start_date": params.start_date,
        "end_date": params.end_date,
        "total_days": total_days,
        "villas": [],
        "average_occupancy_rate": 0.0,
        "total_revenue": Decimal('0.00')
    }
    
    total_occupancy_rate = 0.0
    
    for villa in villas:
        # Count occupied days
        occupied_days_query = db.query(func.count(BookingVilla.id)).join(
            Booking, BookingVilla.booking_id == Booking.id
        ).filter(
            BookingVilla.villa_id == villa.id,
            Booking.status.in_(["confirmed", "ongoing", "completed"]),
            or_(
                # Booking starts within the date range
                and_(
                    Booking.check_in >= params.start_date,
                    Booking.check_in <= params.end_date
                ),
                # Booking ends within the date range
                and_(
                    Booking.check_out >= params.start_date,
                    Booking.check_out <= params.end_date
                ),
                # Booking spans the entire date range
                and_(
                    Booking.check_in <= params.start_date,
                    Booking.check_out >= params.end_date
                )
            )
        )
        
        occupied_days = occupied_days_query.scalar() or 0
        
        # Calculate occupancy rate
        occupancy_rate = (occupied_days / total_days) * 100 if total_days > 0 else 0
        
        # Calculate revenue
        revenue_query = db.query(func.sum(Payment.amount)).join(
            Booking, Payment.booking_id == Booking.id
        ).join(
            BookingVilla, Booking.id == BookingVilla.booking_id
        ).filter(
            BookingVilla.villa_id == villa.id,
            Payment.status == "paid",
            Booking.check_in >= params.start_date,
            Booking.check_in <= params.end_date
        )
        
        revenue = revenue_query.scalar() or Decimal('0.00')
        
        # Add to result
        villa_item = {
            "villa_id": villa.id,
            "villa_name": villa.name,
            "total_days": total_days,
            "occupied_days": occupied_days,
            "occupancy_rate": occupancy_rate,
            "revenue": revenue
        }
        
        result["villas"].append(villa_item)
        result["total_revenue"] += revenue
        total_occupancy_rate += occupancy_rate
    
    # Calculate average occupancy rate
    if villas:
        result["average_occupancy_rate"] = total_occupancy_rate / len(villas)
    
    return result


def get_booking_status_report(db: Session, params: ReportBookingStatusParams) -> Dict[str, Any]:
    """
    Generate booking status report
    
    Args:
        db: Database session
        params: Report parameters
        
    Returns:
        Dict[str, Any]: Booking status report
    """
    # Query bookings
    booking_query = db.query(Booking).filter(
        Booking.created_at >= params.start_date,
        Booking.created_at <= params.end_date
    )
    
    if params.status:
        booking_query = booking_query.filter(Booking.status == params.status)
    
    bookings = booking_query.all()
    
    # Count bookings by status
    status_counts = defaultdict(int)
    for booking in bookings:
        status_counts[booking.status] += 1
    
    total_bookings = len(bookings)
    
    # Calculate percentages
    status_breakdown = []
    for status, count in status_counts.items():
        percentage = (count / total_bookings) * 100 if total_bookings > 0 else 0
        status_breakdown.append({
            "status": status,
            "count": count,
            "percentage": percentage
        })
    
    # Sort by count descending
    status_breakdown.sort(key=lambda x: x["count"], reverse=True)
    
    # Create result
    result = {
        "start_date": params.start_date,
        "end_date": params.end_date,
        "total_bookings": total_bookings,
        "status_breakdown": status_breakdown
    }
    
    return result


def get_revenue_report(db: Session, params: ReportRevenueParams) -> Dict[str, Any]:
    """
    Generate revenue report
    
    Args:
        db: Database session
        params: Report parameters
        
    Returns:
        Dict[str, Any]: Revenue report
    """
    # Initialize result
    result = {
        "start_date": params.start_date,
        "end_date": params.end_date,
        "group_by": params.group_by,
        "total_revenue": Decimal('0.00'),
        "total_bookings": 0,
        "average_booking_value": Decimal('0.00'),
        "items": []
    }
    
    # Base query for payments
    payment_query = db.query(
        Payment.id,
        Payment.amount,
        Payment.payment_date,
        Booking.id.label("booking_id")
    ).join(
        Booking, Payment.booking_id == Booking.id
    ).filter(
        Payment.status == "paid",
        Payment.payment_date >= params.start_date,
        Payment.payment_date <= params.end_date
    )
    
    # Filter by villa if specified
    if params.villa_id:
        payment_query = payment_query.join(
            BookingVilla, Booking.id == BookingVilla.booking_id
        ).filter(
            BookingVilla.villa_id == params.villa_id
        )
    
    payments = payment_query.all()
    
    # Group payments by period
    if params.group_by == "day":
        grouped_payments = _group_payments_by_day(payments)
    elif params.group_by == "week":
        grouped_payments = _group_payments_by_week(payments)
    elif params.group_by == "month":
        grouped_payments = _group_payments_by_month(payments)
    elif params.group_by == "year":
        grouped_payments = _group_payments_by_year(payments)
    elif params.group_by == "villa":
        grouped_payments = _group_payments_by_villa(db, payments)
    else:
        # Default to day
        grouped_payments = _group_payments_by_day(payments)
    
    # Calculate totals
    total_revenue = Decimal('0.00')
    total_bookings = set()
    
    for period, period_payments in grouped_payments.items():
        period_revenue = sum(payment.amount for payment in period_payments)
        period_bookings = set(payment.booking_id for payment in period_payments)
        
        result["items"].append({
            "period": period,
            "revenue": period_revenue,
            "bookings_count": len(period_bookings),
            "average_booking_value": period_revenue / len(period_bookings) if period_bookings else Decimal('0.00')
        })
        
        total_revenue += period_revenue
        total_bookings.update(period_bookings)
    
    # Sort items by period
    result["items"].sort(key=lambda x: x["period"])
    
    # Set totals
    result["total_revenue"] = total_revenue
    result["total_bookings"] = len(total_bookings)
    result["average_booking_value"] = total_revenue / len(total_bookings) if total_bookings else Decimal('0.00')
    
    return result


def _group_payments_by_day(payments: List[Any]) -> Dict[str, List[Any]]:
    """Group payments by day"""
    grouped = defaultdict(list)
    for payment in payments:
        day = payment.payment_date.strftime("%Y-%m-%d")
        grouped[day].append(payment)
    return grouped


def _group_payments_by_week(payments: List[Any]) -> Dict[str, List[Any]]:
    """Group payments by week"""
    grouped = defaultdict(list)
    for payment in payments:
        # ISO week format: YYYY-WW
        week = payment.payment_date.strftime("%Y-%W")
        grouped[week].append(payment)
    return grouped


def _group_payments_by_month(payments: List[Any]) -> Dict[str, List[Any]]:
    """Group payments by month"""
    grouped = defaultdict(list)
    for payment in payments:
        month = payment.payment_date.strftime("%Y-%m")
        grouped[month].append(payment)
    return grouped


def _group_payments_by_year(payments: List[Any]) -> Dict[str, List[Any]]:
    """Group payments by year"""
    grouped = defaultdict(list)
    for payment in payments:
        year = payment.payment_date.strftime("%Y")
        grouped[year].append(payment)
    return grouped


def _group_payments_by_villa(db: Session, payments: List[Any]) -> Dict[str, List[Any]]:
    """Group payments by villa"""
    # Get booking to villa mapping
    booking_ids = [payment.booking_id for payment in payments]
    booking_villas = db.query(BookingVilla).filter(
        BookingVilla.booking_id.in_(booking_ids)
    ).all()
    
    # Create mapping of booking_id to villa_id
    booking_to_villa = {}
    for bv in booking_villas:
        booking_to_villa[bv.booking_id] = bv.villa_id
    
    # Get villa names
    villa_ids = list(set(booking_to_villa.values()))
    villas = db.query(Villa).filter(Villa.id.in_(villa_ids)).all()
    villa_names = {villa.id: villa.name for villa in villas}
    
    # Group payments by villa
    grouped = defaultdict(list)
    for payment in payments:
        villa_id = booking_to_villa.get(payment.booking_id)
        if villa_id:
            villa_name = villa_names.get(villa_id, f"Villa {villa_id}")
            grouped[villa_name].append(payment)
    
    return grouped


def get_top_villas_report(db: Session, start_date: date, end_date: date, limit: int = 5) -> Dict[str, Any]:
    """
    Generate top villas report
    
    Args:
        db: Database session
        start_date: Start date
        end_date: End date
        limit: Maximum number of villas to return
        
    Returns:
        Dict[str, Any]: Top villas report
    """
    # Calculate total days in the date range
    delta = end_date - start_date
    total_days = delta.days + 1
    
    # Query villas with bookings and payments
    villas_data = []
    
    villas = db.query(Villa).all()
    
    for villa in villas:
        # Count bookings
        bookings_count = db.query(func.count(BookingVilla.id)).join(
            Booking, BookingVilla.booking_id == Booking.id
        ).filter(
            BookingVilla.villa_id == villa.id,
            Booking.check_in >= start_date,
            Booking.check_in <= end_date
        ).scalar() or 0
        
        # Calculate revenue
        revenue = db.query(func.sum(Payment.amount)).join(
            Booking, Payment.booking_id == Booking.id
        ).join(
            BookingVilla, Booking.id == BookingVilla.booking_id
        ).filter(
            BookingVilla.villa_id == villa.id,
            Payment.status == "paid",
            Booking.check_in >= start_date,
            Booking.check_in <= end_date
        ).scalar() or Decimal('0.00')
        
        # Calculate occupancy rate
        occupied_days = db.query(func.count(BookingVilla.id)).join(
            Booking, BookingVilla.booking_id == Booking.id
        ).filter(
            BookingVilla.villa_id == villa.id,
            Booking.status.in_(["confirmed", "ongoing", "completed"]),
            or_(
                # Booking starts within the date range
                and_(
                    Booking.check_in >= start_date,
                    Booking.check_in <= end_date
                ),
                # Booking ends within the date range
                and_(
                    Booking.check_out >= start_date,
                    Booking.check_out <= end_date
                ),
                # Booking spans the entire date range
                and_(
                    Booking.check_in <= start_date,
                    Booking.check_out >= end_date
                )
            )
        ).scalar() or 0
        
        occupancy_rate = (occupied_days / total_days) * 100 if total_days > 0 else 0
        
        villas_data.append({
            "villa_id": villa.id,
            "villa_name": villa.name,
            "bookings_count": bookings_count,
            "revenue": revenue,
            "occupancy_rate": occupancy_rate
        })
    
    # Sort by revenue descending
    villas_data.sort(key=lambda x: x["revenue"], reverse=True)
    
    # Limit results
    villas_data = villas_data[:limit]
    
    # Create result
    result = {
        "start_date": start_date,
        "end_date": end_date,
        "villas": villas_data
    }
    
    return result


def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    """
    Generate dashboard summary
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: Dashboard summary
    """
    # Get current date
    today = date.today()
    
    # Calculate date ranges
    last_30_days_start = today - timedelta(days=30)
    current_month_start = date(today.year, today.month, 1)
    next_month_start = date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
    current_month_end = next_month_start - timedelta(days=1)
    
    # Count bookings by status
    total_bookings = db.query(func.count(Booking.id)).scalar() or 0
    
    pending_bookings = db.query(func.count(Booking.id)).filter(
        Booking.status == "pending"
    ).scalar() or 0
    
    ongoing_bookings = db.query(func.count(Booking.id)).filter(
        Booking.status == "ongoing"
    ).scalar() or 0
    
    completed_bookings = db.query(func.count(Booking.id)).filter(
        Booking.status == "completed"
    ).scalar() or 0
    
    cancelled_bookings = db.query(func.count(Booking.id)).filter(
        Booking.status == "cancelled"
    ).scalar() or 0
    
    # Calculate revenue
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == "paid"
    ).scalar() or Decimal('0.00')
    
    pending_payments = db.query(func.sum(Payment.amount)).filter(
        Payment.status == "pending"
    ).scalar() or Decimal('0.00')
    
    # Calculate occupancy rate for current month
    villas_count = db.query(func.count(Villa.id)).scalar() or 0
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    total_villa_days = villas_count * days_in_month
    
    occupied_days = db.query(func.count(BookingVilla.id)).join(
        Booking, BookingVilla.booking_id == Booking.id
    ).filter(
        Booking.status.in_(["confirmed", "ongoing", "completed"]),
        or_(
            # Booking starts within the current month
            and_(
                Booking.check_in >= current_month_start,
                Booking.check_in <= current_month_end
            ),
            # Booking ends within the current month
            and_(
                Booking.check_out >= current_month_start,
                Booking.check_out <= current_month_end
            ),
            # Booking spans the entire current month
            and_(
                Booking.check_in <= current_month_start,
                Booking.check_out >= current_month_end
            )
        )
    ).scalar() or 0
    
    occupancy_rate = (occupied_days / total_villa_days) * 100 if total_villa_days > 0 else 0
    
    # Get top villas
    top_villas_data = get_top_villas_report(db, last_30_days_start, today, limit=3)
    
    # Get recent bookings
    recent_bookings = db.query(Booking).order_by(
        Booking.created_at.desc()
    ).limit(5).all()
    
    recent_bookings_data = []
    for booking in recent_bookings:
        recent_bookings_data.append({
            "id": booking.id,
            "booking_code": booking.booking_code,
            "customer_name": booking.customer.name if booking.customer else "N/A",
            "check_in": booking.check_in,
            "check_out": booking.check_out,
            "status": booking.status,
            "created_at": booking.created_at
        })
    
    # Get revenue chart data for last 12 months
    revenue_chart_data = []
    for i in range(11, -1, -1):
        month_start = date(today.year, today.month, 1) - timedelta(days=i * 30)
        month_end = date(today.year, today.month, 1) - timedelta(days=(i-1) * 30 - 1)
        
        month_revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.status == "paid",
            Payment.payment_date >= month_start,
            Payment.payment_date <= month_end
        ).scalar() or Decimal('0.00')
        
        revenue_chart_data.append({
            "month": month_start.strftime("%b %Y"),
            "revenue": float(month_revenue)
        })
    
    # Create result
    result = {
        "total_bookings": total_bookings,
        "pending_bookings": pending_bookings,
        "ongoing_bookings": ongoing_bookings,
        "completed_bookings": completed_bookings,
        "cancelled_bookings": cancelled_bookings,
        "total_revenue": total_revenue,
        "pending_payments": pending_payments,
        "occupancy_rate": occupancy_rate,
        "top_villas": top_villas_data["villas"],
        "recent_bookings": recent_bookings_data,
        "revenue_chart": revenue_chart_data
    }
    
    return result


def _get_payment_status(amount_paid: Decimal, amount_due: Decimal, due_date: Optional[date]) -> str:
    """
    Determine payment status based on amount paid, amount due, and due date.
    
    Args:
        amount_paid: Amount already paid
        amount_due: Amount still due
        due_date: Due date for payment (optional)
    
    Returns:
        str: Payment status string
    """
    if amount_due <= 0:
        return "paid"
    elif amount_paid > 0 and amount_due > 0:
        return "partially_paid"
    elif amount_paid == 0:
        # Check if overdue
        if due_date and due_date < date.today():
            return "overdue"
        return "pending"
    else:
        return "pending"


def get_sales_report(db: Session, params: SalesReportParams) -> Dict[str, Any]:
    """
    Generate sales report from invoices
    
    Args:
        db: Database session
        params: Report parameters
    
    Returns:
        Dict[str, Any]: Sales report data
    """
    from app.models.user import User
    
    # Build query for invoices within date range (using check_in date)
    # Filter invoices where check_in falls within the date range OR check_in is null (standalone invoices)
    invoice_query = db.query(Invoice).filter(
        or_(
            and_(
                Invoice.check_in.isnot(None),
                Invoice.check_in >= params.start_date,
                Invoice.check_in <= params.end_date
            ),
            Invoice.check_in.is_(None)
        )
    )
    
    # Filter by sales person IDs if provided
    if params.sales_person_ids:
        invoice_query = invoice_query.filter(
            Invoice.sales_person_id.in_(params.sales_person_ids)
        )
    
    # Get all invoices
    invoices = invoice_query.all()
    
    # Process each invoice and calculate payment status
    items = []
    total_sales_amount = Decimal('0.00')
    total_paid_amount = Decimal('0.00')
    
    today = date.today()
    
    # Get booking IDs that need to be looked up
    invoice_booking_ids = []
    for invoice in invoices:
        bid = invoice.booking_id
        if bid is not None:
            invoice_booking_ids.append(bid)
    
    # Build a lookup dict for bookings
    booking_lookup = {}
    if invoice_booking_ids:
        from app.models.booking import Booking
        booking_records = db.query(Booking.id, Booking.booking_code).filter(
            Booking.id.in_(invoice_booking_ids)
        ).all()
        booking_lookup = {b.id: b.booking_code for b in booking_records}
    
    for invoice in invoices:
        # Determine payment status
        # Use invoice's due_date for overdue check
        # Get due_date value - need to handle SQLAlchemy Column type for type checker
        payment_status = _get_payment_status(
            Decimal(str(invoice.amount_paid)),
            Decimal(str(invoice.amount_due)),
            invoice.due_date if invoice.due_date is not None else None  # type: ignore[arg-type]
        )
        
        # Filter by payment status if provided
        if params.payment_status and payment_status != params.payment_status:
            continue
        
        # Get customer name
        customer_name = invoice.customer.name if invoice.customer else "N/A"
        
        # Get sales person name
        sales_person_name = None
        if invoice.sales_person:
            sales_person_name = invoice.sales_person.full_name
        
        # Get booking info if invoice has a booking
        booking_id = invoice.booking_id
        booking_code = None
        if booking_id is not None:
            booking_code = booking_lookup.get(booking_id) 
        # we only have the booking_id foreign key
        
        # Use invoice's check_in/check_out if available, otherwise None
        check_in = invoice.check_in
        check_out = invoice.check_out
        
        # Create item
        item = {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "booking_id": booking_id,
            "booking_code": booking_code,
            "customer_name": customer_name,
            "sales_person_name": sales_person_name,
            "check_in": check_in,
            "check_out": check_out,
            "total": invoice.total,
            "amount_paid": invoice.amount_paid,
            "amount_due": invoice.amount_due,
            "payment_status": payment_status
        }
        
        items.append(item)
        total_sales_amount += invoice.total
        total_paid_amount += invoice.amount_paid
    
    # Calculate difference
    total_difference = total_sales_amount - total_paid_amount
    
    # Sort items by issue_date descending
    items.sort(key=lambda x: x.get("invoice_id"), reverse=True)
    
    # Create result
    result = {
        "start_date": params.start_date,
        "end_date": params.end_date,
        "items": items,
        "total_sales_amount": total_sales_amount,
        "total_paid_amount": total_paid_amount,
        "total_difference": total_difference
    }
    
    return result