from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.dependencies import get_db, get_current_user
from DATA.schemas.responses.notifications import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

def get_notification_service(session: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(session=session)

@router.get("", response_model=dict, summary="Get User Notifications", response_description="List of notifications for the user")
def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: dict[str, str] = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Retrieve notifications for the authenticated user.
    
    Can be filtered to fetch only unread notifications by setting `unread_only=true`.
    Used for populating the notification dropdown/bell icon in the frontend.
    """
    notifications = notification_service.get_user_notifications(UUID(current_user["id"]), unread_only, limit)
    return {"success": True, "data": [NotificationResponse.model_validate(n).model_dump() for n in notifications]}

@router.put("/{notification_id}/read", response_model=dict, summary="Mark Notification as Read", response_description="The updated notification")
def mark_notification_as_read(
    notification_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Mark a specific notification as read.
    
    Call this endpoint when the user clicks on a notification or opens the notification panel.
    """
    notification = notification_service.mark_as_read(notification_id, UUID(current_user["id"]))
    return {"success": True, "data": NotificationResponse.model_validate(notification).model_dump()}
