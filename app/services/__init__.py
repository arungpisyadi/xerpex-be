"""
Business logic services for the XerpeX ERP System
"""
from app.services.auth import authenticate_user, create_user as create_auth_user, log_user_login, generate_token
from app.services.user import (
    get_user, get_user_by_email, get_user_by_username, get_users,
    create_user, update_user, delete_user, get_user_activities
)
from app.services.villa import (
    get_villa, get_villas, create_villa, update_villa, delete_villa,
    get_villa_availability, create_villa_availability, update_villa_availability,
    check_villa_availability
)
from app.services.booking import (
    get_booking, get_booking_by_code, get_bookings, create_booking, update_booking,
    update_booking_status, delete_booking, get_booking_details,
    add_booking_villa, remove_booking_villa,
    add_booking_package, remove_booking_package,
    add_booking_addon, remove_booking_addon
)
from app.services.payment import (
    get_payment, get_payments, create_payment, update_payment,
    update_payment_status, delete_payment, get_payment_details,
    get_invoice, get_invoice_by_number, get_invoices,
    create_invoice, update_invoice, update_invoice_status, delete_invoice,
    link_payment_to_invoice, get_booking_payment_summary
)
from app.services.report import (
    get_villa_occupancy_report, get_booking_status_report,
    get_revenue_report, get_top_villas_report, get_dashboard_summary
)