"""
KPI services for the XerpeX ERP System
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from calendar import month_name

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
import pytz

from app.models.customer import Customer
from app.models.booking import Booking
from app.models.survey import Survey
from app.models.quote import Quote
from app.models.payment import Invoice
from app.models.user import User
from app.models.target import Target
from app.schemas.kpi import KPIResponse, KPIStatsResponse, MonthlyRevenuePerSalesResponse, SalesPersonPerformance
from app.utils.security import get_user_filter_condition


class KPIService:
    """Service class for KPI calculations"""
    
    @staticmethod
    def _get_jakarta_timezone():
        """Get Jakarta timezone (Asia/Jakarta UTC+7:00)"""
        return pytz.timezone('Asia/Jakarta')
    
    @staticmethod
    def _get_current_month_range():
        """Get current month start and end dates in Jakarta timezone"""
        jakarta_tz = KPIService._get_jakarta_timezone()
        now_jakarta = datetime.now(jakarta_tz)
        
        # Start of current month
        start_of_month = now_jakarta.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Start of next month
        if now_jakarta.month == 12:
            start_of_next_month = now_jakarta.replace(year=now_jakarta.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_of_next_month = now_jakarta.replace(month=now_jakarta.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return start_of_month, start_of_next_month, now_jakarta
    
    @staticmethod
    def _get_previous_month_range():
        """Get previous month start and end dates in Jakarta timezone"""
        jakarta_tz = KPIService._get_jakarta_timezone()
        now_jakarta = datetime.now(jakarta_tz)
        
        # Start of previous month
        if now_jakarta.month == 1:
            start_of_prev_month = now_jakarta.replace(year=now_jakarta.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_of_prev_month = now_jakarta.replace(month=now_jakarta.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Start of current month (end of previous month)
        start_of_current_month = now_jakarta.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return start_of_prev_month, start_of_current_month
    
    @staticmethod
    def _calculate_growth_percentage(current_total: int, previous_total: int) -> float:
        """
        Calculate growth percentage using the specified formula:
        ((current_month - previous_month) / previous_month) * 100 if previous_month > 0,
        else 100% if current_month > 0
        """
        if previous_total > 0:
            return ((current_total - previous_total) / previous_total) * 100
        elif current_total > 0:
            return 100.0
        else:
            return 0.0
    
    @staticmethod
    def _get_period_description(dt: datetime) -> str:
        """Get period description like 'January 2025'"""
        return f"{month_name[dt.month]} {dt.year}"
    
    @staticmethod
    def get_customers_kpi(db: Session, current_user: User) -> KPIResponse:
        """
        Get customers KPI with user isolation
        
        Args:
            db: Database session
            current_user: Current user for role-based access control
            
        Returns:
            KPIResponse: Customer KPI data
        """
        start_current, end_current, now_jakarta = KPIService._get_current_month_range()
        start_prev, end_prev = KPIService._get_previous_month_range()
        
        # Convert to UTC for database queries
        start_current_utc = start_current.astimezone(pytz.UTC)
        end_current_utc = end_current.astimezone(pytz.UTC)
        start_prev_utc = start_prev.astimezone(pytz.UTC)
        end_prev_utc = end_prev.astimezone(pytz.UTC)
        
        # Build base query with user isolation
        base_query = db.query(Customer)
        user_filter = get_user_filter_condition(current_user, Customer.user_id)
        if user_filter is not True:
            base_query = base_query.filter(user_filter)
        
        # Get current month total
        current_total = base_query.filter(
            and_(
                Customer.created_at >= start_current_utc,
                Customer.created_at < end_current_utc
            )
        ).count()
        
        # Get previous month total
        previous_total = base_query.filter(
            and_(
                Customer.created_at >= start_prev_utc,
                Customer.created_at < end_prev_utc
            )
        ).count()
        
        # Calculate growth percentage
        growth_percentage = KPIService._calculate_growth_percentage(current_total, previous_total)
        
        return KPIResponse(
            total=current_total,
            growth_percentage=growth_percentage,
            previous_month_total=previous_total,
            period=KPIService._get_period_description(now_jakarta)
        )
    
    @staticmethod
    def get_bookings_kpi(db: Session, current_user: User) -> KPIResponse:
        """
        Get bookings KPI (no user isolation)
        
        Args:
            db: Database session
            current_user: Current user (not used for isolation but kept for consistency)
            
        Returns:
            KPIResponse: Booking KPI data
        """
        start_current, end_current, now_jakarta = KPIService._get_current_month_range()
        start_prev, end_prev = KPIService._get_previous_month_range()
        
        # Convert to UTC for database queries
        start_current_utc = start_current.astimezone(pytz.UTC)
        end_current_utc = end_current.astimezone(pytz.UTC)
        start_prev_utc = start_prev.astimezone(pytz.UTC)
        end_prev_utc = end_prev.astimezone(pytz.UTC)
        
        # Get current month total (no user isolation for bookings)
        current_total = db.query(Booking).filter(
            and_(
                Booking.created_at >= start_current_utc,
                Booking.created_at < end_current_utc
            )
        ).count()
        
        # Get previous month total
        previous_total = db.query(Booking).filter(
            and_(
                Booking.created_at >= start_prev_utc,
                Booking.created_at < end_prev_utc
            )
        ).count()
        
        # Calculate growth percentage
        growth_percentage = KPIService._calculate_growth_percentage(current_total, previous_total)
        
        return KPIResponse(
            total=current_total,
            growth_percentage=growth_percentage,
            previous_month_total=previous_total,
            period=KPIService._get_period_description(now_jakarta)
        )
    
    @staticmethod
    def get_surveys_kpi(db: Session, current_user: User) -> KPIResponse:
        """
        Get surveys KPI (no user isolation)
        
        Args:
            db: Database session
            current_user: Current user (not used for isolation but kept for consistency)
            
        Returns:
            KPIResponse: Survey KPI data
        """
        start_current, end_current, now_jakarta = KPIService._get_current_month_range()
        start_prev, end_prev = KPIService._get_previous_month_range()
        
        # Convert to UTC for database queries
        start_current_utc = start_current.astimezone(pytz.UTC)
        end_current_utc = end_current.astimezone(pytz.UTC)
        start_prev_utc = start_prev.astimezone(pytz.UTC)
        end_prev_utc = end_prev.astimezone(pytz.UTC)
        
        # Get current month total (no user isolation for surveys)
        current_total = db.query(Survey).filter(
            and_(
                Survey.created_at >= start_current_utc,
                Survey.created_at < end_current_utc
            )
        ).count()
        
        # Get previous month total
        previous_total = db.query(Survey).filter(
            and_(
                Survey.created_at >= start_prev_utc,
                Survey.created_at < end_prev_utc
            )
        ).count()
        
        # Calculate growth percentage
        growth_percentage = KPIService._calculate_growth_percentage(current_total, previous_total)
        
        return KPIResponse(
            total=current_total,
            growth_percentage=growth_percentage,
            previous_month_total=previous_total,
            period=KPIService._get_period_description(now_jakarta)
        )
    
    @staticmethod
    def get_quotes_kpi(db: Session, current_user: User) -> KPIResponse:
        """
        Get quotes KPI with user isolation
        
        Args:
            db: Database session
            current_user: Current user for role-based access control
            
        Returns:
            KPIResponse: Quote KPI data
        """
        start_current, end_current, now_jakarta = KPIService._get_current_month_range()
        start_prev, end_prev = KPIService._get_previous_month_range()
        
        # Convert to UTC for database queries
        start_current_utc = start_current.astimezone(pytz.UTC)
        end_current_utc = end_current.astimezone(pytz.UTC)
        start_prev_utc = start_prev.astimezone(pytz.UTC)
        end_prev_utc = end_prev.astimezone(pytz.UTC)
        
        # Build base query with user isolation
        base_query = db.query(Quote)
        user_filter = get_user_filter_condition(current_user, Quote.user_id)
        if user_filter is not True:
            base_query = base_query.filter(user_filter)
        
        # Get current month total
        current_total = base_query.filter(
            and_(
                Quote.created_at >= start_current_utc,
                Quote.created_at < end_current_utc
            )
        ).count()
        
        # Get previous month total
        previous_total = base_query.filter(
            and_(
                Quote.created_at >= start_prev_utc,
                Quote.created_at < end_prev_utc
            )
        ).count()
        
        # Calculate growth percentage
        growth_percentage = KPIService._calculate_growth_percentage(current_total, previous_total)
        
        return KPIResponse(
            total=current_total,
            growth_percentage=growth_percentage,
            previous_month_total=previous_total,
            period=KPIService._get_period_description(now_jakarta)
        )
    
    @staticmethod
    def get_all_kpis(db: Session, current_user: User) -> KPIStatsResponse:
        """
        Get all KPIs in a single response
        
        Args:
            db: Database session
            current_user: Current user for role-based access control
            
        Returns:
            KPIStatsResponse: All KPI data
        """
        return KPIStatsResponse(
            customers=KPIService.get_customers_kpi(db, current_user),
            bookings=KPIService.get_bookings_kpi(db, current_user),
            surveys=KPIService.get_surveys_kpi(db, current_user),
            quotes=KPIService.get_quotes_kpi(db, current_user)
        )
    
    @staticmethod
    def _get_scalar_value(value):
        """Get scalar value from a possibly Column-wrapped value"""
        if hasattr(value, '__iter__'):
            # It's a Column, return the first element or default
            return value
        return value
    
    @staticmethod
    def get_monthly_revenue_per_sales(db: Session, current_user: User) -> MonthlyRevenuePerSalesResponse:
        """
        Get monthly revenue per sales person for the current month
        
        Args:
            db: Database session
            current_user: Current user for role-based access control
            
        Returns:
            MonthlyRevenuePerSalesResponse: Revenue per sales person data
        """
        jakarta_tz = KPIService._get_jakarta_timezone()
        now_jakarta = datetime.now(jakarta_tz)
        
        current_year = now_jakarta.year
        current_month = now_jakarta.month
        month_name_str = month_name[current_month]
        
        # Get start and end of current month
        start_current, end_current, _ = KPIService._get_current_month_range()
        
        # Convert to UTC for database queries
        start_current_utc = start_current.astimezone(pytz.UTC)
        end_current_utc = end_current.astimezone(pytz.UTC)
        
        # Get all sales users with scalar values
        sales_users = db.query(User.id, User.full_name).filter(
            User.role == 'sales',
            User.is_active == True
        ).all()
        
        # Build base query for invoices with sales_person_id
        base_query = db.query(
            Invoice.sales_person_id,
            func.sum(Invoice.total).label('total_revenue')
        ).filter(
            and_(
                Invoice.sales_person_id.isnot(None),
                Invoice.check_in >= start_current_utc,
                Invoice.check_in < end_current_utc
            )
        )
        
        # Apply user isolation - admin/finance see all, sales see only their own
        user_filter = get_user_filter_condition(current_user, Invoice.sales_person_id)
        if user_filter is not True:
            base_query = base_query.filter(user_filter)
        
        # Group by sales_person_id
        base_query = base_query.group_by(Invoice.sales_person_id)
        
        # Execute query
        results = base_query.all()
        
        # Create a mapping of sales_person_id to revenue
        revenue_by_sales = {row.sales_person_id: float(row.total_revenue or 0) for row in results}
        
        # Query sales targets for current month and year
        targets = db.query(Target).filter(
            and_(
                Target.year == current_year,
                Target.month == current_month
            )
        ).all()
        
        # Create a mapping of user_id to target amount (using adjusted_target_amount)
        target_by_user = {}
        for target in targets:
            adjusted = float(target.adjusted_target_amount) if target.adjusted_target_amount is not None else 0.0
            original = float(target.target_amount) if target.target_amount is not None else 0.0
            target_amount = adjusted if adjusted > 0 else original
            target_by_user[target.user_id] = target_amount
        
        # Build sales performance list
        sales_performance = []
        
        # If current user is admin/finance, show all sales users with their revenue
        # If current user is sales, show only their own performance
        if current_user.role in ['admin', 'finance']:
            for user_id, user_name in sales_users:
                user_id_int = int(user_id)
                user_name_str = str(user_name) if user_name else f"User {user_id_int}"
                revenue = revenue_by_sales.get(user_id_int, 0.0)
                target = target_by_user.get(user_id_int, 0.0)
                sales_performance.append(SalesPersonPerformance(
                    sales_person_id=user_id_int,
                    sales_person_name=user_name_str,
                    revenues=revenue,
                    target=target
                ))
        else:
            # Sales user - show only their own data
            current_user_id = int(current_user.id)  # type: ignore
            current_user_name = str(current_user.full_name) if current_user.full_name else f"User {current_user_id}"  # type: ignore
            revenue = revenue_by_sales.get(current_user_id, 0.0)
            target = target_by_user.get(current_user_id, 0.0)
            sales_performance.append(SalesPersonPerformance(
                sales_person_id=current_user_id,
                sales_person_name=current_user_name,
                revenues=revenue,
                target=target
            ))
        
        return MonthlyRevenuePerSalesResponse(
            month=month_name_str,
            year=str(current_year),
            sales_performance=sales_performance
        )


# Service functions for backward compatibility and easier import
def get_customers_kpi(db: Session, current_user: User) -> KPIResponse:
    """Get customers KPI"""
    return KPIService.get_customers_kpi(db, current_user)


def get_bookings_kpi(db: Session, current_user: User) -> KPIResponse:
    """Get bookings KPI"""
    return KPIService.get_bookings_kpi(db, current_user)


def get_surveys_kpi(db: Session, current_user: User) -> KPIResponse:
    """Get surveys KPI"""
    return KPIService.get_surveys_kpi(db, current_user)


def get_quotes_kpi(db: Session, current_user: User) -> KPIResponse:
    """Get quotes KPI"""
    return KPIService.get_quotes_kpi(db, current_user)


def get_all_kpis(db: Session, current_user: User) -> KPIStatsResponse:
    """Get all KPIs"""
    return KPIService.get_all_kpis(db, current_user)


def get_monthly_revenue_per_sales(db: Session, current_user: User) -> MonthlyRevenuePerSalesResponse:
    """Get monthly revenue per sales person"""
    return KPIService.get_monthly_revenue_per_sales(db, current_user)