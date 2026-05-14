from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_admin_service
from app.dependencies import get_current_user
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", summary="Admin Dashboard Stats", response_description="High-level system statistics")
def dashboard(
    current_user: dict[str, str] = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict[str, object]:
    """
    Retrieve aggregated statistics for the admin dashboard.
    
    Provides high-level metrics such as total users, active campaigns, and platform growth.
    The frontend can use this to populate the main admin overview cards.
    """
    return admin_service.get_dashboard()


@router.get("/users", summary="List All Users", response_description="List of registered users with roles")
def users(
    current_user: dict[str, str] = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict[str, object]:
    """
    Retrieve a list of all registered users on the platform.
    
    Returns standard user details, roles (SME or CREATOR), and their account status.
    This is intended for the admin user management table on the frontend.
    """
    return admin_service.list_users()


@router.get("/platform-health", summary="Platform Health & Status", response_description="System health indicators")
def platform_health(
    current_user: dict[str, str] = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict[str, object]:
    """
    Check the overall health of the platform and external API integrations.
    
    Returns the status of background workers, database connectivity, and YouTube API quota limits.
    """
    return admin_service.get_platform_health()
