"""
Target services for the XerpeX ERP System
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from fastapi import HTTPException, status

from app.models.target import Target
from app.models.target_achievement import TargetAchievement
from app.models.payment import Invoice
from app.models.user import User


class TargetService:
    """Service class for target-related operations"""

    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.db = db

    def calculate_monthly_achievement(self, user_id: int, year: int, month: int) -> float:
        """
        Calculate monthly achievement from invoice revenue

        Args:
            user_id: User ID (sales person)
            year: Year
            month: Month

        Returns:
            float: Total achieved amount
        """
        try:
            # Sum total from paid invoices for the sales person in the given month/year
            result = self.db.query(func.sum(Invoice.total)).filter(
                and_(
                    Invoice.sales_person_id == user_id,
                    Invoice.status == 'paid',
                    extract('year', Invoice.issue_date) == year,
                    extract('month', Invoice.issue_date) == month
                )
            ).scalar()

            return float(result) if result else 0.0
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calculating monthly achievement: {str(e)}"
            )

    def calculate_carry_over_target(self, user_id: int, year: int, month: int) -> float:
        """
        Calculate carry-over target from previous month

        Args:
            user_id: User ID
            year: Year
            month: Month

        Returns:
            float: Carry-over amount
        """
        try:
            # Determine previous month
            if month == 1:
                prev_year = year - 1
                prev_month = 12
            else:
                prev_year = year
                prev_month = month - 1

            # Get previous month's achievement
            prev_achievement = self.db.query(TargetAchievement).filter(
                and_(
                    TargetAchievement.user_id == user_id,
                    TargetAchievement.year == prev_year,
                    TargetAchievement.month == prev_month
                )
            ).first()

            if not prev_achievement:
                return 0.0

            # Calculate unmet target
            unmet = max(0.0, prev_achievement.target_amount - prev_achievement.achieved_amount)
            return float(unmet)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calculating carry-over target: {str(e)}"
            )

    def recalculate_targets(self, user_id: int, year: int, month: int) -> float:
        """
        Recalculate targets with carry-over

        Args:
            user_id: User ID
            year: Year
            month: Month

        Returns:
            float: Adjusted target amount
        """
        try:
            # Calculate carry-over
            carried_over = self.calculate_carry_over_target(user_id, year, month)

            # Get current target
            current_target = self.db.query(Target).filter(
                and_(
                    Target.user_id == user_id,
                    Target.year == year,
                    Target.month == month
                )
            ).first()

            current_amount = float(current_target.target_amount) if current_target else 0.0
            adjusted_amount = current_amount + carried_over

            # Upsert target
            if current_target:
                current_target.carried_over_amount = carried_over
                current_target.adjusted_target_amount = adjusted_amount
                current_target.updated_at = datetime.utcnow()
            else:
                new_target = Target(
                    user_id=user_id,
                    year=year,
                    month=month,
                    target_amount=current_amount,
                    carried_over_amount=carried_over,
                    adjusted_target_amount=adjusted_amount
                )
                self.db.add(new_target)

            self.db.commit()
            return adjusted_amount
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error recalculating targets: {str(e)}"
            )

    def get_targets_overview(self) -> Dict[str, Any]:
        """
        Get targets overview for admin

        Returns:
            Dict containing overview data
        """
        try:
            current_year = datetime.utcnow().year
            current_month = datetime.utcnow().month

            # Get total yearly target
            total_yearly = self.db.query(func.sum(Target.target_amount)).filter(
                and_(
                    Target.year == current_year,
                    Target.month <= current_month
                )
            ).scalar() or 0.0

            # Get current month achievement
            current_achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
                and_(
                    TargetAchievement.year == current_year,
                    TargetAchievement.month == current_month
                )
            ).scalar() or 0.0

            # Calculate percentage
            percentage = (current_achievement / total_yearly * 100) if total_yearly > 0 else 0.0

            # Get monthly data (simplified)
            monthly_data = []
            chart_data = []

            return {
                "total_yearly_target": float(total_yearly),
                "current_month_achievement": float(current_achievement),
                "achievement_percentage": float(percentage),
                "monthly_data": monthly_data,
                "chart_data": chart_data
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting targets overview: {str(e)}"
            )

    def get_my_performance(self, user_id: int, year: int) -> Dict[str, Any]:
        """
        Get performance data for a specific user

        Args:
            user_id: User ID
            year: Year

        Returns:
            Dict containing performance data
        """
        try:
            # Get monthly targets
            monthly_targets = self.db.query(Target).filter(
                and_(
                    Target.user_id == user_id,
                    Target.year == year
                )
            ).all()

            # Get monthly achievements
            monthly_achievements = self.db.query(TargetAchievement).filter(
                and_(
                    TargetAchievement.user_id == user_id,
                    TargetAchievement.year == year
                )
            ).all()

            # Calculate totals
            total_target = sum(t.adjusted_target_amount for t in monthly_targets)
            total_achievement = sum(a.achieved_amount for a in monthly_achievements)
            percentage = (total_achievement / total_target * 100) if total_target > 0 else 0.0

            return {
                "user_id": user_id,
                "year": year,
                "monthly_targets": [
                    {
                        "month": t.month,
                        "target_amount": float(t.target_amount),
                        "carried_over": float(t.carried_over_amount),
                        "adjusted_target": float(t.adjusted_target_amount)
                    } for t in monthly_targets
                ],
                "monthly_achievements": [
                    {
                        "month": a.month,
                        "achieved_amount": float(a.achieved_amount),
                        "target_amount": float(a.target_amount),
                        "percentage": float(a.achievement_percentage)
                    } for a in monthly_achievements
                ],
                "total_achievement": float(total_achievement),
                "achievement_percentage": float(percentage)
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting my performance: {str(e)}"
            )

    def get_company_performance(self, year: int) -> Dict[str, Any]:
        """
        Get company-wide performance data

        Args:
            year: Year

        Returns:
            Dict containing company performance data
        """
        try:
            # Get total yearly target
            total_yearly = self.db.query(func.sum(Target.target_amount)).filter(
                Target.year == year
            ).scalar() or 0.0

            # Get total achievement
            total_achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
                TargetAchievement.year == year
            ).scalar() or 0.0

            # Calculate percentage
            percentage = (total_achievement / total_yearly * 100) if total_yearly > 0 else 0.0

            # Get user performances
            user_performances = []
            users = self.db.query(User).filter(User.role == 'sales').all()

            for user in users:
                user_data = self.get_my_performance(user.id, year)
                user_performances.append({
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "total_achievement": user_data["total_achievement"],
                    "achievement_percentage": user_data["achievement_percentage"]
                })

            return {
                "year": year,
                "total_yearly_target": float(total_yearly),
                "total_achievement": float(total_achievement),
                "achievement_percentage": float(percentage),
                "user_performances": user_performances
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting company performance: {str(e)}"
            )

    def recalculate_monthly_targets_for_all_users(self) -> None:
        """
        Recalculate monthly targets for all sales users.
        This is called by the scheduled job on the 1st of every month at 2:00 AM.
        """
        try:
            # Get the previous month (since we run on the 1st)
            now = datetime.utcnow()
            if now.month == 1:
                prev_year = now.year - 1
                prev_month = 12
            else:
                prev_year = now.year
                prev_month = now.month - 1

            # Get all sales users
            sales_users = self.db.query(User).filter(User.role == 'sales').all()

            recalculated_count = 0
            for user in sales_users:
                try:
                    # Recalculate targets for this user
                    self.recalculate_targets(user.id, prev_year, prev_month)
                    recalculated_count += 1
                except Exception as e:
                    # Log error but continue with other users
                    print(f"Error recalculating targets for user {user.id}: {str(e)}")

            print(f"Monthly target recalculation completed for {recalculated_count} sales users")

        except Exception as e:
            print(f"Error in monthly target recalculation: {str(e)}")
            raise

    def get_all_targets(self) -> List[Target]:
        """
        Get all targets

        Returns:
            List[Target]: List of all targets
        """
        try:
            return self.db.query(Target).all()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting all targets: {str(e)}"
            )

    def update_target(self, target_id: int, target_data) -> Target:
        """
        Update a specific target

        Args:
            target_id: Target ID
            target_data: Updated target data

        Returns:
            Target: Updated target

        Raises:
            HTTPException: If target not found
        """
        try:
            target = self.db.query(Target).filter(Target.id == target_id).first()
            if not target:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target not found"
                )

            # Update fields
            for field, value in target_data.dict(exclude_unset=True).items():
                if hasattr(target, field):
                    setattr(target, field, value)

            target.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(target)
            return target
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating target: {str(e)}"
            )

    def delete_target(self, target_id: int) -> None:
        """
        Delete a specific target

        Args:
            target_id: Target ID

        Raises:
            HTTPException: If target not found
        """
        try:
            target = self.db.query(Target).filter(Target.id == target_id).first()
            if not target:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target not found"
                )

            self.db.delete(target)
            self.db.commit()
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting target: {str(e)}"
            )