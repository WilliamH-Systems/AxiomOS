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
                memory_info = (
                    f"\\n\\nAvailable memories: {list(state.long_term_memory.keys())}"
                )
                response += memory_info
            elif state.context.get("processing_remember"):
                response = "I've saved our conversation to your long-term memory."

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
                memory_keys = list(state.long_term_memory.keys())[:5]
                memory_summary = f"User's long-term memories: {memory_keys}"
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
