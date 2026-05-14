from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.dependencies import get_db, get_current_user
from DATA.schemas.requests.messages import SendMessageRequest
from DATA.schemas.responses.messages import MessageResponse
from app.services.message_service import MessageService

router = APIRouter(prefix="/collaborations", tags=["messages"])

def get_message_service(session: Session = Depends(get_db)) -> MessageService:
    return MessageService(session=session)

@router.get("/{collaboration_id}/messages", response_model=dict)
def get_messages(
    collaboration_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    messages = message_service.get_messages(collaboration_id, UUID(current_user["id"]))
    return {"success": True, "data": [MessageResponse.model_validate(m).model_dump() for m in messages]}

@router.post("/{collaboration_id}/messages", response_model=dict)
def send_message(
    collaboration_id: UUID,
    payload: SendMessageRequest,
    current_user: dict[str, str] = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    message = message_service.send_message(collaboration_id, UUID(current_user["id"]), payload)
    return {"success": True, "data": MessageResponse.model_validate(message).model_dump()}
