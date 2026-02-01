from typing import Dict, Any, Optional, List, AsyncGenerator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from dataclasses import dataclass, field
import uuid
from datetime import datetime, timedelta
import asyncio
import json

from groq import Groq

from .database import db_manager
from .database import User as DBUser, Session as DBSession, LongTermMemory as DBMemory
from .redis_manager import redis_manager
from .config import config
from .models import AgentRequestModel, AgentResponseModel, StreamChunkModel, TokenStream


@dataclass
class AgentState:
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    messages: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    long_term_memory: Dict[str, Any] = field(default_factory=dict)


class AxiomOSAgent:
    def __init__(self):
        self.groq_client = Groq(api_key=config.groq.api_key)
        self.memory = MemorySaver()

    def run(self, request: AgentRequestModel) -> AgentResponseModel:
        """Simple, production-ready agent execution"""
        initial_state = AgentState(
            session_id=request.session_id, messages=[request.message]
        )

        # Process through simple, reliable workflow
        state = self._authenticate(initial_state)
        state = self._load_memory(state)
        state = self._process_message(state)
        state = self._save_memory(state)
        state = self._respond(state)

        return AgentResponseModel(
            response=state.messages[-1] if state.messages else "No response generated",
            session_id=state.session_id,
            user_id=state.user_id,
            context=state.context,
        )

    def _authenticate(self, state: AgentState) -> AgentState:
        """Authenticate or create session"""
        if not state.session_id:
            state.session_id = str(uuid.uuid4())

        session_db = db_manager.get_session()
        try:
            session = (
                session_db.query(DBSession)
                .filter(
                    DBSession.session_id == state.session_id,
                    DBSession.expires_at > datetime.now(),
                )
                .first()
            )

            if session:
                state.user_id = session.user_id
            else:
                new_session = DBSession(
                    user_id=1,  # Default user
                    session_id=state.session_id,
                    expires_at=datetime.now()
                    + timedelta(seconds=config.session_timeout),
                )
                session_db.add(new_session)
                session_db.commit()
                state.user_id = new_session.user_id

        finally:
            session_db.close()

        return state

    def _load_memory(self, state: AgentState) -> AgentState:
        """Load session and long-term memory"""
        # Load session memory from Redis
        if state.session_id:
            session_data = redis_manager.get_session_data(state.session_id)
            if session_data:
                state.context.update(session_data.get("context", {}))

        # Load long-term memory from PostgreSQL
        if state.user_id:
            db_session = db_manager.get_session()
            try:
                memories = (
                    db_session.query(DBMemory)
                    .filter(DBMemory.user_id == state.user_id)
                    .all()
                )

                for memory in memories:
                    if memory.key and memory.value:
                        state.long_term_memory[memory.key] = memory.value

            finally:
                db_session.close()

        return state

    def _process_message(self, state: AgentState) -> AgentState:
        """Process messages and detect commands"""
        if not state.messages:
            return state

        last_message = state.messages[-1]

        # Detect special commands
        if "remember" in last_message.lower():
            state.context["processing_remember"] = True
        elif "recall" in last_message.lower():
            state.context["processing_recall"] = True
        elif "delete" in last_message.lower() and (
            "memory" in last_message.lower() or "memories" in last_message.lower()
        ):
            state.context["processing_delete"] = True

        return state

    def _save_memory(self, state: AgentState) -> AgentState:
        """Save memory to Redis and PostgreSQL"""
        # Save session context to Redis
        if state.session_id and state.context:
            redis_manager.set_session_data(
                state.session_id, {"context": state.context}, ttl=config.session_timeout
            )

        # Save important data to long-term memory
        if state.user_id and state.context.get("processing_remember"):
            db_session = db_manager.get_session()
            try:
                memory_key = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                memory_value = {
                    "messages": state.messages[-5:] if len(state.messages) > 1 else [],
                    "context": state.context,
                }

                new_memory = DBMemory(
                    user_id=state.user_id,
                    key=memory_key,
                    value=json.dumps(memory_value),
                )
                db_session.add(new_memory)
                db_session.commit()

            finally:
                db_session.close()

        # Process memory deletion requests
        if state.user_id and state.context.get("processing_delete"):
            state = self._process_memory_deletion(state)

        return state

    def _process_memory_deletion(self, state: AgentState) -> AgentState:
        """Carefully process memory deletion requests using Groq AI"""
        if not state.messages or not state.user_id:
            return state

        last_message = state.messages[-1]

        # Get current memories for context
        memories = {}
        db_session = db_manager.get_session()
        try:
            memory_records = (
                db_session.query(DBMemory)
                .filter(DBMemory.user_id == state.user_id)
                .all()
            )

            for memory in memory_records:
                if memory.key and memory.value:
                    memories[memory.key] = memory.value

        finally:
            db_session.close()

        if not memories:
            state.context["delete_result"] = "No memories found to delete."
            return state

        # Use Groq to make an intelligent decision about memory deletion
        try:
            memory_list = []
            for key, value in memories.items():
                try:
                    parsed_value = (
                        json.loads(value) if isinstance(value, str) else value
                    )
                    if isinstance(parsed_value, dict) and "messages" in parsed_value:
                        messages = parsed_value["messages"]
                        if messages:
                            msg_summary = "; ".join(str(m)[:100] for m in messages[:3])
                            memory_list.append(f"{key}: {msg_summary}")
                        else:
                            memory_list.append(f"{key}: [empty conversation]")
                    else:
                        memory_list.append(f"{key}: {str(value)[:100]}...")
                except:
                    memory_list.append(f"{key}: {str(value)[:100]}...")

            memories_text = "\n".join(memory_list)

            # Prompt Groq to decide about deletion
            decision_prompt = f"""
You are AxiomOS, a personal assistant. The user wants to delete memories. You must decide this carefully.

Available memories:
{memories_text}

User request: "{last_message}"

Respond with ONLY ONE of these options:
1. "DELETE_ALL" - if the user explicitly requests to delete all memories using phrases like "delete all memories", "clear all memories", "remove everything"
2. "DELETE_SPECIFIC:memory_key_here" - if the user wants to delete a specific memory and clearly identifies it, AND the content seems non-critical or redundant
3. "DELETE_NONE:safety_concern" - if deletion is unsafe, unclear, could cause data loss, or the memory contains important information

Guidelines:
- Allow deletion of redundant or trivial conversations (like test messages, simple questions)
- Protect important personal information, preferences, and meaningful conversations
- Require explicit language for "delete all" requests
- Be conservative but reasonable

Your response must be exactly one of the three formats above.
"""

            chat_completion = self.groq_client.chat.completions.create(
                model=config.groq.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a careful AI assistant that prioritizes user safety and data integrity.",
                    },
                    {"role": "user", "content": decision_prompt},
                ],
                max_tokens=50,
                temperature=0.1,
                stream=False,
            )

            decision = chat_completion.choices[0].message.content.strip()

            # Execute the deletion decision
            if decision.startswith("DELETE_ALL:"):
                return self._execute_delete_all(state, memories)
            elif decision.startswith("DELETE_SPECIFIC:"):
                memory_key = decision.split(":", 1)[1].strip()
                return self._execute_delete_specific(state, memory_key, memories)
            elif decision.startswith("DELETE_NONE:"):
                reason = (
                    decision.split(":", 1)[1].strip()
                    if ":" in decision
                    else "Safety concern"
                )
                state.context["delete_result"] = (
                    f"I cannot delete the memory(ies) because: {reason}"
                )
            else:
                state.context["delete_result"] = (
                    "I'm not sure how to handle this deletion request. Please be more specific."
                )

        except Exception as e:
            state.context["delete_result"] = (
                f"Error processing deletion request: {str(e)}"
            )

        return state

    def _execute_delete_all(self, state: AgentState, memories: dict) -> AgentState:
        """Execute deletion of all memories"""
        try:
            db_session = db_manager.get_session()
            try:
                deleted_count = (
                    db_session.query(DBMemory)
                    .filter(DBMemory.user_id == state.user_id)
                    .delete()
                )
                db_session.commit()
                state.context["delete_result"] = (
                    f"Successfully deleted {deleted_count} memories."
                )
            finally:
                db_session.close()
        except Exception as e:
            state.context["delete_result"] = f"Failed to delete memories: {str(e)}"
        return state

    def _execute_delete_specific(
        self, state: AgentState, memory_key: str, memories: dict
    ) -> AgentState:
        """Execute deletion of a specific memory"""
        if memory_key not in memories:
            state.context["delete_result"] = f"Memory '{memory_key}' not found."
            return state

        try:
            db_session = db_manager.get_session()
            try:
                deleted_count = (
                    db_session.query(DBMemory)
                    .filter(
                        DBMemory.user_id == state.user_id, DBMemory.key == memory_key
                    )
                    .delete()
                )
                db_session.commit()

                if deleted_count > 0:
                    state.context["delete_result"] = (
                        f"Successfully deleted memory '{memory_key}'."
                    )
                else:
                    state.context["delete_result"] = (
                        f"Failed to delete memory '{memory_key}'."
                    )
            finally:
                db_session.close()
        except Exception as e:
            state.context["delete_result"] = (
                f"Failed to delete memory '{memory_key}': {str(e)}"
            )
        return state

    def _respond(self, state: AgentState) -> AgentState:
        """Generate intelligent response using Groq"""
        if not state.messages:
            return state

        last_message = state.messages[-1]

        # Use Groq for intelligent responses
        try:
            # Build conversation context
            conversation_context = []

            # Add long-term memories as context
            if state.long_term_memory:
                memory_keys = list(state.long_term_memory.keys())[:5]
                memory_summary = f"User's long-term memories: {memory_keys}"
                conversation_context.append(
                    {"role": "system", "content": memory_summary}
                )

            # Add recent conversation
            if len(state.messages) > 1:
                for msg in state.messages[
                    -3:-1
                ]:  # Last 3 messages excluding current one
                    if msg:
                        conversation_context.append({"role": "user", "content": msg})

            # Add current message
            if last_message:
                conversation_context.append({"role": "user", "content": last_message})

            # Generate response using Groq
            chat_completion = self.groq_client.chat.completions.create(
                model=config.groq.model,
                messages=conversation_context,
                max_tokens=config.groq.max_tokens,
                temperature=config.groq.temperature,
                stream=False,
            )

            response = chat_completion.choices[0].message.content

            # Handle special commands
            if state.context.get("processing_recall"):
                if state.long_term_memory:
                    memory_content = []
                    for key, value in state.long_term_memory.items():
                        try:
                            import json

                            if isinstance(value, str):
                                try:
                                    parsed_value = json.loads(value)
                                    if (
                                        isinstance(parsed_value, dict)
                                        and "messages" in parsed_value
                                    ):
                                        messages = parsed_value["messages"]
                                        # Format messages nicely
                                        if messages:
                                            msg_texts = []
                                            for msg in messages:
                                                if isinstance(msg, str):
                                                    msg_texts.append(f'"{msg}"')
                                                elif (
                                                    isinstance(msg, dict)
                                                    and "content" in msg
                                                ):
                                                    msg_texts.append(
                                                        f'"{msg["content"]}"'
                                                    )
                                            memory_content.append(
                                                f"Memory '{key}': {', '.join(msg_texts)}"
                                            )
                                        else:
                                            memory_content.append(
                                                f"Memory '{key}': [empty conversation]"
                                            )
                                    else:
                                        memory_content.append(
                                            f"Memory '{key}': {value}"
                                        )
                                except json.JSONDecodeError:
                                    memory_content.append(f"Memory '{key}': {value}")
                            else:
                                memory_content.append(f"Memory '{key}': {value}")
                        except Exception as e:
                            memory_content.append(
                                f"Memory '{key}': Error reading content - {e}"
                            )

                    if memory_content:
                        memory_info = (
                            "\\n\\nHere's what I remember about you:\\n"
                            + "\\n".join(memory_content)
                        )
                    else:
                        memory_info = (
                            "\\n\\nI found memories but couldn't extract their content."
                        )
                else:
                    memory_info = "\\n\\nI don't have any memories stored about you."

                response += memory_info
            elif state.context.get("processing_remember"):
                response = "I've saved our conversation to your long-term memory."
            elif state.context.get("processing_delete"):
                delete_result = state.context.get(
                    "delete_result", "Memory deletion request processed."
                )
                response = f"{delete_result}"

        except Exception as e:
            response = f"I received your message: '{last_message}'. I'm AxiomOS, your personal assistant. (Note: Groq API error: {str(e)})"

        if response and isinstance(response, str):
            state.messages.append(response)

        return state

    async def run_stream(self, request: AgentRequestModel) -> TokenStream:
        """Run agent with streaming response"""
        initial_state = AgentState(
            session_id=request.session_id, messages=[request.message]
        )

        # Process through simple, reliable workflow
        state = self._authenticate(initial_state)
        state = self._load_memory(state)
        state = self._process_message(state)
        state = self._save_memory(state)

        # Now stream the response
        try:
            # Build conversation context for streaming
            conversation_context = []

            if state.long_term_memory:
                # Build better memory context for streaming
                memory_content = []
                for key, value in list(state.long_term_memory.items())[:5]:
                    try:
                        import json

                        if isinstance(value, str):
                            try:
                                parsed_value = json.loads(value)
                                if (
                                    isinstance(parsed_value, dict)
                                    and "messages" in parsed_value
                                ):
                                    messages = parsed_value["messages"]
                                    if messages:
                                        msg_texts = []
                                        for msg in messages:
                                            if isinstance(msg, str):
                                                msg_texts.append(f'"{msg}"')
                                            elif (
                                                isinstance(msg, dict)
                                                and "content" in msg
                                            ):
                                                msg_texts.append(f'"{msg["content"]}"')
                                        memory_content.append(
                                            f"{key}: {', '.join(msg_texts)}"
                                        )
                                    else:
                                        memory_content.append(f"{key}: [empty]")
                                else:
                                    memory_content.append(
                                        f"{key}: {str(value)[:100]}..."
                                    )
                            except json.JSONDecodeError:
                                memory_content.append(f"{key}: {str(value)[:100]}...")
                        else:
                            memory_content.append(f"{key}: {str(value)[:100]}...")
                    except Exception:
                        memory_content.append(f"{key}: [error reading]")

                memory_summary = (
                    f"User's long-term memories: {'; '.join(memory_content)}"
                )
                conversation_context.append(
                    {"role": "system", "content": memory_summary}
                )

            if len(state.messages) > 1:
                for msg in state.messages[-3:-1]:
                    if msg:
                        conversation_context.append({"role": "user", "content": msg})

            if request.message:
                conversation_context.append(
                    {"role": "user", "content": request.message}
                )

            # Stream from Groq
            chat_stream = self.groq_client.chat.completions.create(
                model=config.groq.model,
                messages=conversation_context,
                max_tokens=config.groq.max_tokens,
                temperature=config.groq.temperature,
                stream=True,
            )

            full_response = ""

            for chunk in chat_stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    token = chunk.choices[0].delta.content
                    full_response += token

                    yield StreamChunkModel(
                        token=token, session_id=state.session_id, is_complete=False
                    )

            # Send final chunk
            yield StreamChunkModel(
                token="",
                session_id=state.session_id,
                is_complete=True,
                final_response=full_response,
            )

            # Save the final response
            if full_response:
                state.messages.append(full_response)
            if state.session_id and state.context:
                redis_manager.set_session_data(
                    state.session_id,
                    {"context": state.context},
                    ttl=config.session_timeout,
                )

        except Exception as e:
            # Fallback response
            error_response = f"Error occurred: {str(e)}"

            yield StreamChunkModel(
                token=error_response,
                session_id=state.session_id,
                is_complete=True,
                final_response=error_response,
            )


# Initialize the global agent instance
axiom_agent = AxiomOSAgent()
