from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    session_id: str | None = Field(None, description="Session ID")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI reply")
    session_id: str | None = Field(None, description="Session ID")


class AudioChatRequest(BaseModel):
    session_id: str | None = Field(None, description="Session ID")
    audio_format: str = Field("webm", description="Audio format")
    sample_rate: int = Field(16000, description="Sample rate")
