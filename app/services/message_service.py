from dataclasses import dataclass
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi import HTTPException
from DATA.models.messages import Message
from DATA.models.campaigns import CampaignCollaboration
from DATA.schemas.requests.messages import SendMessageRequest

@dataclass
class MessageService:
    session: Session

    def get_messages(self, collaboration_id: UUID, current_user_id: UUID) -> list[Message]:
        collab = self.session.query(CampaignCollaboration).filter(CampaignCollaboration.id == collaboration_id).first()
        if not collab:
            raise HTTPException(status_code=404, detail="Collaboration not found")
        
        from DATA.models.users import CreatorProfile, SMEProfile, User
        
        user = self.session.query(User).filter(User.id == current_user_id).first()
        is_admin = user and user.role == "ADMIN"
        
        creator_profile = self.session.query(CreatorProfile).filter(CreatorProfile.id == collab.creator_id).first()
        sme_profile = self.session.query(SMEProfile).filter(SMEProfile.id == collab.campaign.sme_id).first()
        
        is_creator = creator_profile and creator_profile.user_id == current_user_id
        is_sme = sme_profile and sme_profile.user_id == current_user_id
        
        if not (is_creator or is_sme or is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to view these messages")
        
        messages = self.session.query(Message).filter(Message.collaboration_id == collaboration_id).order_by(Message.created_at.asc()).all()
        return messages

    def send_message(self, collaboration_id: UUID, current_user_id: UUID, payload: SendMessageRequest) -> Message:
        collab = self.session.query(CampaignCollaboration).filter(CampaignCollaboration.id == collaboration_id).first()
        if not collab:
            raise HTTPException(status_code=404, detail="Collaboration not found")
            
        from DATA.models.users import CreatorProfile, SMEProfile, User
        
        user = self.session.query(User).filter(User.id == current_user_id).first()
        is_admin = user and user.role == "ADMIN"
        
        creator_profile = self.session.query(CreatorProfile).filter(CreatorProfile.id == collab.creator_id).first()
        sme_profile = self.session.query(SMEProfile).filter(SMEProfile.id == collab.campaign.sme_id).first()
        
        is_creator = creator_profile and creator_profile.user_id == current_user_id
        is_sme = sme_profile and sme_profile.user_id == current_user_id
        
        if not (is_creator or is_sme or is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to send messages to this collaboration")
            
        message = Message(
            collaboration_id=collaboration_id,
            sender_id=current_user_id,
            content=payload.content
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message
