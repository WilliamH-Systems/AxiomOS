from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from .chat_message import ChatMessage


@dataclass(frozen=True)
class AgentState:
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    messages: List[ChatMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    long_term_memory: Dict[str, Any] = field(default_factory=dict)
    detected_commands: List[str] = field(default_factory=list)

    def with_user_id(self, user_id: int) -> "AgentState":
        return self._replace(user_id=user_id)

    def with_session_id(self, session_id: str) -> "AgentState":
        return self._replace(session_id=session_id)

    def with_message(self, message: ChatMessage) -> "AgentState":
        return self._replace(messages=self.messages + [message])

    def with_messages(self, messages: List[ChatMessage]) -> "AgentState":
        return self._replace(messages=messages)

    def with_context(self, **kwargs) -> "AgentState":
        new_context = {**self.context, **kwargs}
        return self._replace(context=new_context)

    def with_long_term_memory(self, memory: Dict[str, Any]) -> "AgentState":
        new_memory = {**self.long_term_memory, **memory}
        return self._replace(long_term_memory=new_memory)

    def with_detected_commands(self, commands: List[str]) -> "AgentState":
        return self._replace(detected_commands=commands)

    def _replace(self, **kwargs) -> "AgentState":
        from dataclasses import replace

        return replace(self, **kwargs)
