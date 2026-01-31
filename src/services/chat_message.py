from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class ChatMessage:
    content: str
    role: ChatRole
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def user_message(
        cls, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> "ChatMessage":
        return cls(
            content=content,
            role=ChatRole.USER,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )

    @classmethod
    def assistant_message(
        cls, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> "ChatMessage":
        return cls(
            content=content,
            role=ChatRole.ASSISTANT,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )

    @classmethod
    def system_message(
        cls, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> "ChatMessage":
        return cls(
            content=content,
            role=ChatRole.SYSTEM,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )
