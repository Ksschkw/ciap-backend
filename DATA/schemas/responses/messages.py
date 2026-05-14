from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collaboration_id: UUID
    sender_id: UUID
    content: str
    created_at: datetime
