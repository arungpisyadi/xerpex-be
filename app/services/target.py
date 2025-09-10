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
from app.schemas.target import TargetOverview, MonthlyData, ChartDataPoint, TopPerformer, YTDMetrics


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

    def recalculate_targets(self, user_id: int, year: int, month: int, target_amount: float = 0.0) -> float:
        """
        Recalculate targets with carry-over

        Args:
            user_id: User ID
            year: Year
            month: Month
            target_amount: Target amount to set (defaults to 0.0 for backward compatibility)

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

            current_amount = float(target_amount) if target_amount > 0.0 else (float(current_target.target_amount) if current_target else 0.0)
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
                    target_amount=float(target_amount) if target_amount > 0.0 else current_amount,
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

    def get_targets_overview(self) -> TargetOverview:
        """
        Get enhanced targets overview for admin

        Returns:
            TargetOverview containing detailed overview data
        """
        try:
            current_year = datetime.utcnow().year
            current_month = datetime.utcnow().month

            # Get total yearly target (sum of all targets for the year)
            total_yearly = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
                Target.year == current_year
            ).scalar() or 0.0

            # Get current month achievement
            current_achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
                and_(
                    TargetAchievement.year == current_year,
                    TargetAchievement.month == current_month
                )
            ).scalar() or 0.0

            # Calculate current month percentage
            current_month_target = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
                and_(
                    Target.year == current_year,
                    Target.month == current_month
                )
            ).scalar() or 0.0

            achievement_percentage = (current_achievement / current_month_target * 100) if current_month_target > 0 else 0.0

            # Get detailed monthly data
            monthly_data = self.get_monthly_data(current_year)

            # Generate chart data
            chart_data = self.generate_chart_data(current_year)

            # Calculate YTD metrics
            ytd_metrics_raw = self.calculate_ytd_metrics(current_year)
            ytd_metrics = YTDMetrics(**ytd_metrics_raw)

            # Get active users count
            active_users_count = self.get_active_users_count()

            # Get top performers
            top_performers = self.get_top_performers(current_year, limit=5)

            return {
                "total_yearly_target": float(total_yearly),
                "current_month_achievement": float(current_achievement),
                "achievement_percentage": float(achievement_percentage),
                "monthly_data": monthly_data,
                "chart_data": chart_data,
                "ytd_metrics": ytd_metrics.model_dump(),
                "active_users_count": active_users_count,
                "top_performers": top_performers
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
            total_yearly_raw = self.db.query(func.sum(Target.target_amount)).filter(
                Target.year == year
            ).scalar()
            total_yearly = float(total_yearly_raw) if total_yearly_raw is not None else 0.0

            # Get total achievement
            total_achievement_raw = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
                TargetAchievement.year == year
            ).scalar()
            total_achievement = float(total_achievement_raw) if total_achievement_raw is not None else 0.0

            # Calculate percentage (both operands are now float)
            percentage = (total_achievement / total_yearly * 100) if total_yearly > 0 else 0.0

            return {
                "year": year,
                "total_yearly_target": float(total_yearly),
                "total_achievement": float(total_achievement),
                "achievement_percentage": float(percentage)
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

    def get_monthly_data(self, year: int) -> List[Dict[str, Any]]:
        """
        Get monthly data for the given year

        Args:
            year: Year

        Returns:
            List of monthly data dictionaries
        """
        try:
            monthly_data = []
            month_names = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]

            for month in range(1, 13):
                # Get target for this month
                target = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
                    and_(
                        Target.year == year,
                        Target.month == month
                    )
                ).scalar() or 0.0

                # Get achievement for this month
                achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
                    and_(
                        TargetAchievement.year == year,
                        TargetAchievement.month == month
                    )
                ).scalar() or 0.0

                # Calculate percentage
                percentage = (achievement / target * 100) if target > 0 else 0.0

                # Get carried over amount
                carried_over = self.db.query(func.sum(Target.carried_over_amount)).filter(
                    and_(
                        Target.year == year,
                        Target.month == month
                    )
                ).scalar() or 0.0

                monthly_data.append({
                    "month": month,
                    "month_name": month_names[month - 1],
                    "target_amount": float(target),
                    "achieved_amount": float(achievement),
                    "achievement_percentage": float(percentage),
                    "carried_over_amount": float(carried_over)
                })

            return monthly_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting monthly data: {str(e)}"
            )

    def generate_chart_data(self, year: int) -> List[Dict[str, Any]]:
        """
        Generate chart data points for the given year

        Args:
            year: Year

        Returns:
            List of chart data point dictionaries
        """
        try:
            chart_data = []
            month_names = [
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
            ]

            for month in range(1, 13):
                # Get target for this month
                target = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
                    and_(
                        Target.year == year,
                        Target.month == month
                    )
                ).scalar() or 0.0

                # Get achievement for this month
                achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
                    and_(
                        TargetAchievement.year == year,
                        TargetAchievement.month == month
                    )
                ).scalar() or 0.0

                chart_data.append({
                    "month": month,
                    "month_name": month_names[month - 1],
                    "target": float(target),
                    "achievement": float(achievement)
                })

            return chart_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating chart data: {str(e)}"
            )

    def calculate_ytd_metrics(self, year: int) -> Dict[str, Any]:
        """
        Calculate year-to-date metrics

        Args:
            year: Year

        Returns:
            Dict containing YTD metrics
        """
        try:
            current_month = datetime.utcnow().month

            # YTD target (sum of targets up to current month)
            ytd_target = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
                and_(
                    Target.year == year,
                    Target.month <= current_month
                )
            ).scalar() or 0.0

            # YTD achievement (sum of achievements up to current month)
            ytd_achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
                and_(
                    TargetAchievement.year == year,
                    TargetAchievement.month <= current_month
                )
            ).scalar() or 0.0

            # YTD percentage
            ytd_percentage = (ytd_achievement / ytd_target * 100) if ytd_target > 0 else 0.0

            return {
                "ytd_target": float(ytd_target),
                "ytd_achievement": float(ytd_achievement),
                "ytd_percentage": float(ytd_percentage)
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calculating YTD metrics: {str(e)}"
            )

    def get_active_users_count(self) -> int:
        """
        Get count of active sales users

        Returns:
            int: Count of active sales users
        """
        try:
            # Count users with role 'sales' who have targets or achievements in current year
            current_year = datetime.utcnow().year

            active_users = self.db.query(func.count(func.distinct(User.id))).filter(
                and_(
                    User.role == 'sales',
                    or_(
                        User.id.in_(
                            self.db.query(Target.user_id).filter(Target.year == current_year)
                        ),
                        User.id.in_(
                            self.db.query(TargetAchievement.user_id).filter(TargetAchievement.year == current_year)
                        )
                    )
                )
            ).scalar() or 0

            return int(active_users)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting active users count: {str(e)}"
            )

    def get_top_performers(self, year: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top performers for the given year

        Args:
            year: Year
            limit: Number of top performers to return

        Returns:
            List of top performer dictionaries
        """
        try:
            # Get users with their total achievements
            performers = self.db.query(
                User.id,
                User.username,
                User.full_name,
                func.sum(TargetAchievement.achieved_amount).label('total_achievement'),
                func.avg(TargetAchievement.achievement_percentage).label('avg_percentage')
            ).join(
                TargetAchievement, User.id == TargetAchievement.user_id
            ).filter(
                and_(
                    User.role == 'sales',
                    TargetAchievement.year == year
                )
            ).group_by(
                User.id, User.username, User.full_name
            ).order_by(
                func.sum(TargetAchievement.achieved_amount).desc()
            ).limit(limit).all()

            top_performers = []
            for performer in performers:
                user_id, username, full_name, total_achievement, avg_percentage = performer

                total_target = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
                    and_(
                        Target.user_id == user_id,
                        Target.year == year
                    )
                ).scalar() or 0.0

                percentage = (total_achievement / total_target * 100) if total_target > 0 else 0.0

                top_performers.append({
                    "user_id": user_id,
                    "username": username,
                    "full_name": full_name or username,
                    "total_achievement": float(total_achievement),
                    "achievement_percentage": float(percentage)
                })

            return top_performers
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting top performers: {str(e)}"
            )

    def get_user_performance_chart(self, year: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get user performance data formatted for bar chart visualization

        Args:
            year: Year for performance data
            user_id: Optional user ID filter

        Returns:
            Dict containing chart-ready performance data
        """
        try:
            # Get sales users (filtered by user_id if provided)
            query = self.db.query(User).filter(User.role == 'sales')
            if user_id:
                query = query.filter(User.id == user_id)
            users = query.all()

            if not users:
                # Return empty chart data if no users found
                return {
                    "year": year,
                    "chart_data": {
                        "labels": [],
                        "datasets": [
                            {
                                "label": "Target Amount",
                                "data": [],
                                "backgroundColor": "rgba(54, 162, 235, 0.5)",
                                "borderColor": "rgba(54, 162, 235, 1)"
                            },
                            {
                                "label": "Achieved Amount",
                                "data": [],
                                "backgroundColor": "rgba(75, 192, 192, 0.5)",
                                "borderColor": "rgba(75, 192, 192, 1)"
                            }
                        ]
                    },
                    "users": [],
                    "total_users": 0,
                    "generated_at": datetime.utcnow()
                }

            labels = []
            target_data = []
            achievement_data = []
            user_details = []

            for user in users:
                # Get user display name
                display_name = user.full_name or user.username
                labels.append(display_name)

                # Aggregate targets for the year
                total_target = self.db.query(func.sum(Target.adjusted_target_amount)).filter(
                    and_(
                        Target.user_id == user.id,
                        Target.year == year
                    )
                ).scalar() or 0.0

                # Aggregate achievements for the year
                total_achievement = self.db.query(func.sum(TargetAchievement.achieved_amount)).filter(
                    and_(
                        TargetAchievement.user_id == user.id,
                        TargetAchievement.year == year
                    )
                ).scalar() or 0.0

                # Calculate achievement percentage
                achievement_percentage = (total_achievement / total_target * 100) if total_target > 0 else 0.0

                # Count months with data
                months_with_targets = self.db.query(func.count(Target.id)).filter(
                    and_(
                        Target.user_id == user.id,
                        Target.year == year
                    )
                ).scalar() or 0

                months_with_achievements = self.db.query(func.count(TargetAchievement.id)).filter(
                    and_(
                        TargetAchievement.user_id == user.id,
                        TargetAchievement.year == year
                    )
                ).scalar() or 0

                months_with_data = max(months_with_targets, months_with_achievements)

                # Add to chart data
                target_data.append(float(total_target))
                achievement_data.append(float(total_achievement))

                # Add to user details
                user_details.append({
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "target_amount": float(total_target),
                    "achieved_amount": float(total_achievement),
                    "achievement_percentage": float(achievement_percentage),
                    "months_with_data": months_with_data
                })

            return {
                "year": year,
                "chart_data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Target Amount",
                            "data": target_data,
                            "backgroundColor": "rgba(54, 162, 235, 0.5)",
                            "borderColor": "rgba(54, 162, 235, 1)"
                        },
                        {
                            "label": "Achieved Amount",
                            "data": achievement_data,
                            "backgroundColor": "rgba(75, 192, 192, 0.5)",
                            "borderColor": "rgba(75, 192, 192, 1)"
                        }
                    ]
                },
                "users": user_details,
                "total_users": len(users),
                "generated_at": datetime.utcnow()
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting user performance chart: {str(e)}"
            )