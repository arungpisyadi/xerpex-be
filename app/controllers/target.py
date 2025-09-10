"""
Targets controllers for the XerpeX ERP System
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.target import (
    TargetCreate,
    TargetUpdate,
    TargetResponse,
    TargetOverview,
    MyPerformance,
    CompanyPerformance,
    UserPerformanceChart,
    MonthlyData,
    ChartDataPoint,
    TopPerformer,
    YTDMetrics
)
from app.services.target import TargetService
from app.utils.security import get_current_active_user, get_current_admin_user

# Admin router for admin-only endpoints
admin_router = APIRouter(prefix="/admin/targets", tags=["admin-targets"])

# General targets router
targets_router = APIRouter(prefix="/targets", tags=["targets"])


@admin_router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def set_target(
    target_data: TargetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Set monthly target for a sales user (Admin only)

    Args:
        target_data: Target creation data
        db: Database session
        current_user: Current admin user

    Returns:
        dict: Success message

    Raises:
        HTTPException: If error occurs
    """

    try:
        target_service = TargetService(db)
        adjusted_target = target_service.recalculate_targets(
            target_data.user_id,
            target_data.year,
            target_data.month,
            target_data.target_amount
        )

        return {
            "message": "Target set successfully",
            "adjusted_target": adjusted_target
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting target: {str(e)}"
        )


@admin_router.get("", response_model=List[TargetResponse])
async def get_all_targets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all targets (Admin only)

    Args:
        db: Database session
        current_user: Current admin user

    Returns:
        List[TargetResponse]: List of all targets

    Raises:
        HTTPException: If error occurs
    """
    try:
        target_service = TargetService(db)
        return target_service.get_all_targets()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting all targets: {str(e)}"
        )


@admin_router.put("/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: int,
    target_data: TargetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update a specific target (Admin only)

    Args:
        target_id: Target ID to update
        target_data: Updated target data
        db: Database session
        current_user: Current admin user

    Returns:
        TargetResponse: Updated target

    Raises:
        HTTPException: If target not found or error occurs
    """
    try:
        target_service = TargetService(db)
        return target_service.update_target(target_id, target_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating target: {str(e)}"
        )


@admin_router.delete("/{target_id}", response_model=dict)
async def delete_target(
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete a specific target (Admin only)

    Args:
        target_id: Target ID to delete
        db: Database session
        current_user: Current admin user

    Returns:
        dict: Success message

    Raises:
        HTTPException: If target not found or error occurs
    """
    try:
        target_service = TargetService(db)
        target_service.delete_target(target_id)
        return {"message": "Target deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting target: {str(e)}"
        )


@admin_router.get("/overview", response_model=TargetOverview)
async def get_targets_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get targets overview (Admin only)

    Args:
        db: Database session
        current_user: Current admin user

    Returns:
        TargetOverview: Overview data
    """
    try:
        target_service = TargetService(db)
        return target_service.get_targets_overview()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting targets overview: {str(e)}"
        )


@targets_router.get("/my-performance", response_model=MyPerformance)
async def get_my_performance(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's performance data

    Args:
        year: Year to get performance for (defaults to current year)
        db: Database session
        current_user: Current user

    Returns:
        MyPerformance: Performance data

    Raises:
        HTTPException: If not sales user or error occurs
    """
    # Only sales users can view their own performance
    if current_user.role != "sales":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    if year is None:
        year = datetime.utcnow().year

    try:
        target_service = TargetService(db)
        return target_service.get_my_performance(current_user.id, year)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting my performance: {str(e)}"
        )


@targets_router.get("/company-performance", response_model=CompanyPerformance)
async def get_company_performance(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get company-wide performance data

    Args:
        year: Year to get performance for (defaults to current year)
        db: Database session
        current_user: Current user

    Returns:
        CompanyPerformance: Company performance data

    Raises:
        HTTPException: If error occurs
    """
    if year is None:
        year = datetime.utcnow().year

    try:
        target_service = TargetService(db)
        return target_service.get_company_performance(year)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting company performance: {str(e)}"
        )


@targets_router.get("/user-performances", response_model=UserPerformanceChart)
async def get_user_performance_chart(
    year: Optional[int] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user performance data formatted for bar chart visualization

    Args:
        year: Year for performance data
        user_id: Optional user ID filter (if provided, returns data for specific user only)
        db: Database session
        current_user: Current user

    Returns:
        UserPerformanceChart: Chart-ready performance data

    Raises:
        HTTPException: If error occurs
    """
    if year is None:
        year = datetime.utcnow().year

    try:
        target_service = TargetService(db)
        return target_service.get_user_performance_chart(year, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user performance chart: {str(e)}"
        )