from dataclasses import dataclass
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from DATA.models.users import Notification

@dataclass
class NotificationService:
    session: Session

    def create_notification(self, user_id: UUID, title: str, body: str, notification_type: str = "GENERAL", action_url: Optional[str] = None, related_entity_id: Optional[UUID] = None) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            action_url=action_url,
            related_entity_id=related_entity_id
        )
        self.session.add(notification)
        self.session.commit()
        self.session.refresh(notification)
        return notification

    def get_user_notifications(self, user_id: UUID, unread_only: bool = False, limit: int = 50) -> List[Notification]:
        query = self.session.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        notification = self.session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(notification)
        return notification
