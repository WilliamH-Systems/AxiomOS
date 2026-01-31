import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .agent_state import AgentState
from ..database import db_manager, LongTermMemory as DBMemory
from ..redis_manager import redis_manager
from ..config import config

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def load_session_memory(self, session_id: str) -> Dict[str, Any]:
        if not session_id:
            return {}

        try:
            session_data = redis_manager.get_session_data(session_id)
            if session_data:
                context = session_data.get("context", {})
                self.logger.debug(
                    f"Loaded session memory for {session_id}: {len(context)} keys"
                )
                return context
        except Exception as e:
            self.logger.warning(f"Redis not available for session memory: {e}")

        return {}

    async def save_session_memory(
        self, session_id: str, context: Dict[str, Any]
    ) -> bool:
        if not session_id or not context:
            return False

        try:
            redis_manager.set_session_data(
                session_id,
                {"context": context},
                ttl=config.session_timeout,
            )
            self.logger.debug(
                f"Saved session memory for {session_id}: {len(context)} keys"
            )
            return True
        except Exception as e:
            self.logger.error(f"Redis not available for saving session: {e}")
            return False

    async def load_long_term_memory(self, user_id: int) -> Dict[str, Any]:
        if not user_id:
            return {}

        try:
            db_session = db_manager.get_session()
            try:
                memories = (
                    db_session.query(DBMemory).filter(DBMemory.user_id == user_id).all()
                )

                long_term_memory = {}
                for memory in memories:
                    try:
                        if isinstance(memory.value, str):
                            long_term_memory[memory.key] = json.loads(memory.value)
                        else:
                            long_term_memory[memory.key] = memory.value
                    except json.JSONDecodeError:
                        long_term_memory[memory.key] = memory.value

                self.logger.debug(
                    f"Loaded long-term memory for user {user_id}: {len(long_term_memory)} keys"
                )
                return long_term_memory

            finally:
                db_session.close()
        except Exception as e:
            self.logger.error(f"Database not available for long-term memory: {e}")
            return {}

    async def save_long_term_memory(self, user_id: int, key: str, value: Any) -> bool:
        if not user_id or not key:
            return False

        try:
            db_session = db_manager.get_session()
            try:
                json_value = json.dumps(value) if not isinstance(value, str) else value

                existing_memory = (
                    db_session.query(DBMemory)
                    .filter(
                        DBMemory.user_id == user_id,
                        DBMemory.key == key,
                    )
                    .first()
                )

                if existing_memory:
                    existing_memory.value = json_value
                else:
                    new_memory = DBMemory(
                        user_id=user_id,
                        key=key,
                        value=json_value,
                    )
                    db_session.add(new_memory)

                db_session.commit()
                self.logger.debug(f"Saved long-term memory for user {user_id}: {key}")
                return True

            finally:
                db_session.close()
        except Exception as e:
            self.logger.error(f"Database not available for saving memory: {e}")
            return False

    async def save_conversation_memory(
        self, user_id: int, messages: list, context: Dict[str, Any]
    ) -> bool:
        if not user_id:
            return False

        try:
            memory_key = (
                f"conversation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            )
            memory_value = {
                "messages": [
                    {"content": msg.content, "role": msg.role.value}
                    if hasattr(msg, "content")
                    else msg
                    for msg in messages[-5:]
                ],
                "context": context,
            }

            return await self.save_long_term_memory(user_id, memory_key, memory_value)
        except Exception as e:
            self.logger.error(f"Failed to save conversation memory: {e}")
            return False

    async def load_all_memory(self, state: AgentState) -> AgentState:
        session_memory = (
            await self.load_session_memory(state.session_id) if state.session_id else {}
        )
        long_term_memory = (
            await self.load_long_term_memory(state.user_id) if state.user_id else {}
        )

        updated_state = state.with_context(**session_memory)
        updated_state = updated_state.with_long_term_memory(long_term_memory)

        self.logger.debug(
            f"Loaded memory - Session: {len(session_memory)} keys, "
            f"Long-term: {len(long_term_memory)} keys"
        )

        return updated_state

    async def save_all_memory(self, state: AgentState) -> AgentState:
        success = True

        if state.session_id and state.context:
            session_success = await self.save_session_memory(
                state.session_id, state.context
            )
            success = success and session_success

        if state.user_id and state.context.get("processing_remember"):
            conversation_success = await self.save_conversation_memory(
                state.user_id, state.messages, state.context
            )
            success = success and conversation_success

        if success:
            self.logger.debug("Successfully saved all memory")
        else:
            self.logger.warning("Some memory operations failed")

        return state
