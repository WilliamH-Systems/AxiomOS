from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MemoryType(str, Enum):
    SESSION = "session"
    LONG_TERM = "long_term"


class MessageModel(BaseModel):
    content: str = Field(
        ..., min_length=1, max_length=10000, description="Message content"
    )
    type: MessageType = Field(default=MessageType.USER, description="Message type")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Message timestamp"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional message metadata"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v.strip()


class SessionModel(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[int] = Field(default=None, description="User ID if authenticated")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Session creation time"
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="Session expiration time"
    )
    context: Dict[str, Any] = Field(default_factory=dict, description="Session context")
    message_history: List[MessageModel] = Field(
        default_factory=list, description="Message history"
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v):
        if not v or len(v) < 8:
            raise ValueError("Session ID must be at least 8 characters long")
        return v


class MemoryModel(BaseModel):
    key: str = Field(..., min_length=1, max_length=255, description="Memory key")
    value: Any = Field(..., description="Memory value")
    type: MemoryType = Field(default=MemoryType.LONG_TERM, description="Memory type")
    user_id: Optional[int] = Field(default=None, description="User ID if user-specific")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Memory creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Memory update time"
    )

    @field_validator("key")
    @classmethod
    def validate_key(cls, v):
        if not v.strip():
            raise ValueError("Memory key cannot be empty")
        return v.strip()


class AgentRequestModel(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=10000, description="User message to process"
    )
    session_id: Optional[str] = Field(
        default=None, description="Session ID for continuity"
    )
    user_id: Optional[int] = Field(default=None, description="User ID if authenticated")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context"
    )
    stream: bool = Field(default=False, description="Whether to stream response")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()


class AgentResponseModel(BaseModel):
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID")
    user_id: Optional[int] = Field(default=None, description="User ID")
    context: Dict[str, Any] = Field(default_factory=dict, description="Updated context")
    tokens_used: Optional[int] = Field(
        default=None, description="Number of tokens used"
    )
    processing_time: Optional[float] = Field(
        default=None, description="Processing time in seconds"
    )


class StreamChunkModel(BaseModel):
    token: str = Field(..., description="Individual token")
    session_id: str = Field(..., description="Session ID")
    is_complete: bool = Field(
        default=False, description="Whether streaming is complete"
    )
    final_response: Optional[str] = Field(
        default=None, description="Complete response when finished"
    )


class UserModel(BaseModel):
    id: Optional[int] = Field(default=None, description="User ID")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    created_at: Optional[datetime] = Field(
        default=None, description="Account creation time"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum() and "_" not in v:
            raise ValueError("Username must be alphanumeric with optional underscores")
        return v.lower()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower()


class ConfigModel(BaseModel):
    groq_api_key: str = Field(..., description="Groq API key")
    groq_model: str = Field(default="llama3-8b-8192", description="Groq model to use")
    max_tokens: int = Field(
        default=1000, ge=1, le=4000, description="Maximum tokens for response"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperature for generation"
    )
    session_timeout: int = Field(
        default=3600, ge=60, description="Session timeout in seconds"
    )

    @field_validator("groq_api_key")
    @classmethod
    def validate_api_key(cls, v):
        if not v.startswith("gsk_"):
            raise ValueError("Invalid Groq API key format")
        return v


# Type alias for async generator
TokenStream = AsyncGenerator[StreamChunkModel, None]
