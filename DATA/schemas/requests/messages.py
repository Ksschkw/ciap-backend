from pydantic import BaseModel, Field

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="The content of the message")
