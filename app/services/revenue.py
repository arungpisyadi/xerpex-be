"""
Revenue services for the XerpeX ERP System
"""
from datetime import datetime, date
from typing import List, Dict, Any
from calendar import month_name
import calendar

from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from fastapi import HTTPException, status
import pytz

from app.models.payment import Invoice
from app.models.target import Target
from app.schemas.revenue import MonthlyRevenueResponse, CurrentMonthPerformanceResponse, CurrentYearPerformanceResponse
from app.utils.security import get_user_filter_condition
from app.models.user import User


class RevenueService:
    """Service class for revenue-related operations"""

    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.db = db

    @staticmethod
    def _get_jakarta_timezone():
        """Get Jakarta timezone (Asia/Jakarta UTC+7:00)"""
        return pytz.timezone('Asia/Jakarta')

    def get_user_filter_condition(self, current_user: User):
        """
        Get user filter condition for revenue data based on user role
        
        Args:
            current_user: Current user
            
        Returns:
            Filter condition for SQLAlchemy query
        """
        return get_user_filter_condition(current_user, Invoice.sales_person_id)

    def get_monthly_revenue(self, year: int, user_id: int) -> MonthlyRevenueResponse:
        """
        Get monthly revenue data for the specified year
        
        Args:
            year: Year for revenue data
            user_id: User ID for filtering (0 for admin/finance to see all)
            
        Returns:
            MonthlyRevenueResponse: Monthly revenue data
        """
        try:
            # Build base query for all invoices
            query = self.db.query(
                func.extract('month', Invoice.issue_date).label('month'),
                func.sum(Invoice.total).label('revenue')
            ).filter(
                func.extract('year', Invoice.issue_date) == year
            )
            
            # Apply user filtering if needed (user_id = 0 means admin/finance sees all)
            if user_id > 0:
                query = query.filter(Invoice.sales_person_id == user_id)
            
            # Group by month and execute query
            query = query.group_by(func.extract('month', Invoice.issue_date))
            results = query.all()
            
            # Convert results to dictionary for easy lookup
            revenue_by_month = {int(month): float(revenue) for month, revenue in results}
            
            # Create monthly data for all 12 months (only revenue amounts, ordered Jan-Dec)
            monthly_data = []
            total_yearly_revenue = 0.0
            
            for month in range(1, 13):
                revenue = revenue_by_month.get(month, 0.0)
                total_yearly_revenue += revenue
                
                # Add only the revenue amount to the list (in chronological order)
                monthly_data.append(float(revenue))
            
            return MonthlyRevenueResponse(
                year=year,
                monthly_data=monthly_data,
                total_yearly_revenue=total_yearly_revenue,
                currency="IDR",
                period=str(year)
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting monthly revenue: {str(e)}"
            )

    def get_monthly_revenue_with_user_isolation(self, year: int, current_user: User) -> MonthlyRevenueResponse:
        """
        Get monthly revenue data with user isolation
        
        Args:
            year: Year for revenue data
            current_user: Current user for role-based access control
            
        Returns:
            MonthlyRevenueResponse: Monthly revenue data
        """
        try:
            # Build base query for all invoices
            query = self.db.query(
                func.extract('month', Invoice.issue_date).label('month'),
                func.sum(Invoice.total).label('revenue')
            ).filter(
                func.extract('year', Invoice.issue_date) == year
            )
            
            # Apply user isolation
            user_filter = self.get_user_filter_condition(current_user)
            if user_filter is not True:
                query = query.filter(user_filter)
            
            # Group by month and execute query
            query = query.group_by(func.extract('month', Invoice.issue_date))
            results = query.all()
            
            # Convert results to dictionary for easy lookup
            revenue_by_month = {int(month): float(revenue) for month, revenue in results}
            
            # Create monthly data for all 12 months (only revenue amounts, ordered Jan-Dec)
            monthly_data = []
            total_yearly_revenue = 0.0
            
            for month in range(1, 13):
                revenue = revenue_by_month.get(month, 0.0)
                total_yearly_revenue += revenue
                
                # Add only the revenue amount to the list (in chronological order)
                monthly_data.append(float(revenue))
            
            return MonthlyRevenueResponse(
                year=year,
                monthly_data=monthly_data,
                total_yearly_revenue=total_yearly_revenue,
                currency="IDR",
                period=str(year)
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting monthly revenue with user isolation: {str(e)}"
            )

    def get_revenue_summary(self, current_user: User) -> Dict[str, Any]:
        """
        Get revenue summary with current year and previous year comparison
        
        Args:
            current_user: Current user for role-based access control
            
        Returns:
            Dict containing revenue summary data
        """
        try:
            jakarta_tz = self._get_jakarta_timezone()
            now_jakarta = datetime.now(jakarta_tz)
            current_year = now_jakarta.year
            previous_year = current_year - 1
            
            # Get current year revenue
            current_year_data = self.get_monthly_revenue_with_user_isolation(current_year, current_user)
            
            # Get previous year revenue  
            previous_year_data = self.get_monthly_revenue_with_user_isolation(previous_year, current_user)
            
            # Calculate growth percentage
            current_total = current_year_data.total_yearly_revenue
            previous_total = previous_year_data.total_yearly_revenue
            
            if previous_total > 0:
                growth_percentage = ((current_total - previous_total) / previous_total) * 100
            elif current_total > 0:
                growth_percentage = 100.0
            else:
                growth_percentage = 0.0
            
            return {
                "current_year": current_year,
                "current_year_revenue": current_total,
                "previous_year": previous_year,
                "previous_year_revenue": previous_total,
                "growth_percentage": growth_percentage,
                "currency": "IDR"
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting revenue summary: {str(e)}"
            )

    def get_current_month_performance(self, current_user: User) -> CurrentMonthPerformanceResponse:
        """
        Get current month performance data with target vs achievement comparison
        
        Args:
            current_user: Current user for role-based access control
            
        Returns:
            CurrentMonthPerformanceResponse: Current month performance data
        """
        try:
            # Get Jakarta timezone for date calculations
            jakarta_tz = self._get_jakarta_timezone()
            now_jakarta = datetime.now(jakarta_tz)
            today_jakarta = now_jakarta.date()
            
            current_year = now_jakarta.year
            current_month = now_jakarta.month
            current_month_name = month_name[current_month]
            
            # Calculate days remaining in current month
            _, last_day = calendar.monthrange(current_year, current_month)
            days_remaining = last_day - today_jakarta.day
            
            # Apply user isolation for target and revenue queries
            user_filter = self.get_user_filter_condition(current_user)
            
            # Get current month target
            target_query = self.db.query(func.sum(Target.target_amount)).filter(
                and_(
                    Target.month == current_month,
                    Target.year == current_year
                )
            )
            
            # Apply user filtering for targets
            if user_filter is not True:
                # For sales users, filter by their user_id in targets
                if current_user.role == 'sales':
                    target_query = target_query.filter(Target.user_id == current_user.id)
                # For admin/finance, get all targets (no additional filter needed)
            
            target_amount = float(target_query.scalar() or 0.0)
            
            # Get current month revenue (all invoices)
            current_revenue_query = self.db.query(func.sum(Invoice.total)).filter(
                and_(
                    func.extract('month', Invoice.issue_date) == current_month,
                    func.extract('year', Invoice.issue_date) == current_year
                )
            )
            
            # Apply user filtering for revenue
            if user_filter is not True:
                current_revenue_query = current_revenue_query.filter(user_filter)
            
            current_revenue = float(current_revenue_query.scalar() or 0.0)
            
            # Get today's revenue (new invoices issued today, regardless of payment status)
            today_revenue_query = self.db.query(func.sum(Invoice.total)).filter(
                func.date(Invoice.issue_date) == today_jakarta
            )
            
            # Apply user filtering for today's revenue
            if user_filter is not True:
                today_revenue_query = today_revenue_query.filter(user_filter)
            
            today_revenue = float(today_revenue_query.scalar() or 0.0)
            
            # Get same month from previous year for growth calculation
            previous_year = current_year - 1
            previous_month_query = self.db.query(func.sum(Invoice.total)).filter(
                and_(
                    func.extract('month', Invoice.issue_date) == current_month,
                    func.extract('year', Invoice.issue_date) == previous_year
                )
            )
            
            # Apply user filtering for previous month revenue
            if user_filter is not True:
                previous_month_query = previous_month_query.filter(user_filter)
            
            previous_month_revenue = float(previous_month_query.scalar() or 0.0)
            
            # Calculate growth metrics
            growth_amount = current_revenue - previous_month_revenue
            if previous_month_revenue > 0:
                growth_percentage = (growth_amount / previous_month_revenue) * 100
            elif current_revenue > 0:
                growth_percentage = 100.0
            else:
                growth_percentage = 0.0
            
            # Calculate performance percentage
            if target_amount > 0:
                performance_percentage = (current_revenue / target_amount) * 100
            else:
                performance_percentage = 0.0
            
            # Create period description
            period = f"{current_month_name} {current_year}"
            
            return CurrentMonthPerformanceResponse(
                month=current_month,
                month_name=current_month_name,
                year=current_year,
                target_amount=target_amount,
                current_revenue=current_revenue,
                today_revenue=today_revenue,
                performance_percentage=float(performance_percentage),
                days_remaining=days_remaining,
                previous_month_revenue=previous_month_revenue,
                growth_amount=growth_amount,
                growth_percentage=growth_percentage,
                period=period
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting current month performance: {str(e)}"
            )

    def get_current_year_performance(self, current_user: User) -> CurrentYearPerformanceResponse:
        """
        Get current year performance data with target vs achievement comparison
        
        Args:
            current_user: Current user for role-based access control
            
        Returns:
            CurrentYearPerformanceResponse: Current year performance data
        """
        try:
            # Get Jakarta timezone for date calculations
            jakarta_tz = self._get_jakarta_timezone()
            now_jakarta = datetime.now(jakarta_tz)
            today_jakarta = now_jakarta.date()
            current_year = now_jakarta.year
            current_month = now_jakarta.month
            
            # Calculate months completed in the current year
            if today_jakarta.day >= calendar.monthrange(current_year, current_month)[1]:
                months_completed = current_month  # Current month is fully completed
            else:
                months_completed = current_month - 1 if current_month > 1 else 0  # Previous months completed
            
            # Apply user isolation for target and revenue queries
            user_filter = self.get_user_filter_condition(current_user)
            
            # Get current year target (sum all months for the year)
            target_query = self.db.query(func.sum(Target.target_amount)).filter(
                Target.year == current_year
            )
            
            # Apply user filtering for targets
            if user_filter is not True:
                # For sales users, filter by their user_id in targets
                if current_user.role == 'sales':
                    target_query = target_query.filter(Target.user_id == current_user.id)
                # For admin/finance, get all targets (no additional filter needed)
            
            target_amount = float(target_query.scalar() or 0.0)
            
            # Get current year revenue (all invoices year-to-date)
            current_revenue_query = self.db.query(func.sum(Invoice.total)).filter(
                func.extract('year', Invoice.issue_date) == current_year
            )
            
            # Apply user filtering for revenue
            if user_filter is not True:
                current_revenue_query = current_revenue_query.filter(user_filter)
            
            current_revenue = float(current_revenue_query.scalar() or 0.0)
            
            # Get previous year revenue for growth calculation
            previous_year = current_year - 1
            previous_year_query = self.db.query(func.sum(Invoice.total)).filter(
                func.extract('year', Invoice.issue_date) == previous_year
            )
            
            # Apply user filtering for previous year revenue
            if user_filter is not True:
                previous_year_query = previous_year_query.filter(user_filter)
            
            previous_year_revenue = float(previous_year_query.scalar() or 0.0)
            
            # Calculate growth metrics
            growth_amount = current_revenue - previous_year_revenue
            if previous_year_revenue > 0:
                growth_percentage = (growth_amount / previous_year_revenue) * 100
            elif current_revenue > 0:
                growth_percentage = 100.0
            else:
                growth_percentage = 0.0
            
            # Calculate performance percentage
            if target_amount > 0:
                performance_percentage = (current_revenue / target_amount) * 100
            else:
                performance_percentage = 0.0
            
            # Create period description
            period = str(current_year)
            
            return CurrentYearPerformanceResponse(
                year=current_year,
                target_amount=target_amount,
                current_revenue=current_revenue,
                performance_percentage=float(performance_percentage),
                months_completed=months_completed,
                previous_year_revenue=previous_year_revenue,
                growth_amount=growth_amount,
                growth_percentage=growth_percentage,
                period=period
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting current year performance: {str(e)}"
            )


# Service functions for backward compatibility and easier import
def get_monthly_revenue(db: Session, year: int, current_user: User) -> MonthlyRevenueResponse:
    """Get monthly revenue with user isolation"""
    service = RevenueService(db)
    return service.get_monthly_revenue_with_user_isolation(year, current_user)


def get_revenue_summary(db: Session, current_user: User) -> Dict[str, Any]:
    """Get revenue summary"""
    service = RevenueService(db)
    return service.get_revenue_summary(current_user)