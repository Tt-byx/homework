from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: str | None = Field(None, description="会话ID")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI回复")
    session_id: str | None = Field(None, description="会话ID")
