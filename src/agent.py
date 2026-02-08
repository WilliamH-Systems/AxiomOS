from typing import Dict, Any, Optional, List, AsyncGenerator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from dataclasses import dataclass, field
import uuid
from datetime import datetime, timedelta
import asyncio
import json

from groq import Groq
from langchain_tavily import TavilySearch
from langsmith import Client as LangSmithClient
from langsmith import traceable
import os

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
        self.tavily_tool = None
        
        # Initialize LangSmith client if tracing is enabled
        self.langsmith_client = None
        if config.langsmith.tracing == "true" and config.langsmith.api_key:
            try:
                self.langsmith_client = LangSmithClient(
                    api_key=config.langsmith.api_key,
                    api_url=config.langsmith.endpoint
                )
                print(f"[DEBUG] LangSmith tracing enabled for project: {config.langsmith.project}")
            except Exception as e:
                print(f"[DEBUG] Failed to initialize LangSmith client: {e}")
                self.langsmith_client = None
        else:
            print("[DEBUG] LangSmith tracing disabled")
            
        if config.tavily.api_key:
            try:
                # TavilySearch will read TAVILY_API_KEY from the environment
                # max_results controls how many results we consider
                self.tavily_tool = TavilySearch(max_results=5)
                print("[DEBUG] Tavily tool initialized")
            except Exception as e:
                print(f"[DEBUG] Failed to init Tavily: {e}")
                self.tavily_tool = None
        else:
            print("[DEBUG] No TAVILY_API_KEY found")

    @traceable(name="axiom_agent_run")
    def run(self, request: AgentRequestModel) -> AgentResponseModel:
        """Simple, production-ready agent execution"""
        initial_state = AgentState(
            session_id=request.session_id, messages=[request.message]
        )

        # Respect per-request web search permission
        if request.allow_web_search:
            initial_state.context["allow_web_search"] = True
            print("[DEBUG] Web search ENABLED for this request")
        else:
            print("[DEBUG] Web search DISABLED for this request")

        # Process through simple, reliable workflow
        state = self._authenticate(initial_state)
        state = self._load_memory(state)
        state = self._process_message(state)
        state = self._execute_command(state)
        state = self._respond(state)
        state = self._save_memory(state)

        return AgentResponseModel(
            response=state.messages[-1] if state.messages else "No response generated",
            session_id=state.session_id,
            user_id=state.user_id,
            context=state.context,
        )

    @traceable
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

    @traceable(name="axiom_agent_web_search")
    def _maybe_add_web_results(self, state: AgentState, query: str) -> AgentState:
        """Use Tavily to fetch web results when allowed and available."""
        if not state.context.get("allow_web_search"):
            print("[DEBUG] Web search not allowed for this request")
            return state
        if not self.tavily_tool:
            state.context["web_search_results"] = "Web search unavailable (missing Tavily key)."
            print("[DEBUG] Tavily tool not available")
            return state

        # Avoid duplicate searches if already set for this query
        cached_query = state.context.get("web_search_query")
        if cached_query and cached_query == query:
            print("[DEBUG] Using cached web search results")
            return state

        try:
            print(f"[DEBUG] Running Tavily search for query: {query}")
            raw = self.tavily_tool.invoke(query)
            print(f"[DEBUG] Raw Tavily result type: {type(raw)}")

            # Normalise Tavily output into a list of result objects
            items = []
            if isinstance(raw, list):
                items = raw
            elif isinstance(raw, dict):
                # Common patterns: {"results": [...]} or similar
                for key in ("results", "data", "documents"):
                    val = raw.get(key)
                    if isinstance(val, list):
                        items = val
                        break
                if not items:
                    items = [raw]
            elif raw is not None:
                items = [raw]

            formatted = []
            for idx, doc in enumerate(items[:5]):
                # Try attributes first (Document-like), then mapping-style, then fallback
                title = None
                content = None
                url = None

                # Attribute-style access (LangChain Document)
                try:
                    title = getattr(doc, "title", None)
                    if title is None and hasattr(doc, "metadata"):
                        meta = getattr(doc, "metadata", {}) or {}
                        if isinstance(meta, dict):
                            title = meta.get("title")
                            url = meta.get("url")
                    content = getattr(doc, "page_content", None) or getattr(doc, "content", None)
                    url = url or getattr(doc, "url", None)
                except Exception:
                    pass

                # Mapping-style access if still missing
                if isinstance(doc, dict):
                    title = title or doc.get("title") or doc.get("url")
                    content = content or doc.get("content") or doc.get("snippet")
                    url = url or doc.get("url")

                # Fallbacks
                if not title:
                    title = f"Result {idx+1}"
                if not content:
                    content = str(doc)
                if not url:
                    url = ""

                snippet = (content[:200] + "...") if len(content) > 200 else content
                formatted.append(f"{idx+1}. {title}\n{snippet}\n{url}")

            if formatted:
                state.context["web_search_results"] = "\n\n".join(formatted)
                state.context["web_search_query"] = query
                state.context["used_web_search"] = True
                print(f"[DEBUG] Tavily returned {len(formatted)} results")
            else:
                state.context["web_search_results"] = "No web results found."
                print("[DEBUG] Tavily returned no results")
        except Exception as e:
            state.context["web_search_results"] = f"Web search error: {str(e)}"
            print(f"[DEBUG] Tavily search error: {e}")

        return state

    @traceable
    def _execute_command(self, state: AgentState) -> AgentState:
        """Execute slash command operations before LLM response"""
        command = state.context.get("command")
        if not command:
            return state

        if command == "save":
            state = self._command_save(state)
        elif command == "recall":
            state = self._command_recall(state)
        elif command == "delete":
            state = self._command_delete(state)
        elif command == "clear":
            state = self._command_clear(state)
        elif command == "help":
            state = self._command_help(state)
        else:
            state.context["command_result"] = (
                f"Unknown command '/{command}'. Available commands: /save, /recall, /delete, /clear, /help."
            )

        # Skip automatic LLM reply and memory save for command interactions
        state.context["skip_llm_response"] = True
        state.context["skip_memory_save"] = True
        # Remove command flag so it doesn't persist
        state.context.pop("command", None)
        state.context.pop("command_arg", None)
        return state

    def _command_save(self, state: AgentState) -> AgentState:
        if not state.user_id:
            state.context["command_result"] = "Cannot save memory: user not authenticated."
            return state

        messages_to_save = state.messages[:-1] if len(state.messages) > 1 else []
        context_snapshot = dict(state.context)
        context_snapshot.pop("command_result", None)
        context_snapshot.pop("skip_llm_response", None)

        db_session = db_manager.get_session()
        try:
            memory_key = f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            memory_value = {
                "messages": messages_to_save,
                "context": context_snapshot,
                "created_by": "manual_save",
            }
            new_memory = DBMemory(
                user_id=state.user_id,
                key=memory_key,
                value=json.dumps(memory_value),
            )
            db_session.add(new_memory)
            db_session.commit()
            state.context["command_result"] = (
                f"Memory saved as '{memory_key}'."
            )
            # Refresh long-term memory cache
            state = self._load_memory(state)
        except Exception as e:
            state.context["command_result"] = f"Failed to save memory: {str(e)}"
        finally:
            db_session.close()

        return state

    def _command_recall(self, state: AgentState) -> AgentState:
        memories = state.long_term_memory or {}
        command_arg = state.context.get("command_arg")

        if not memories:
            state.context["command_result"] = "No memories available to recall."
            return state

        if command_arg:
            key = command_arg.strip()
            memory_value = memories.get(key)
            if not memory_value:
                state.context["command_result"] = f"Memory '{key}' not found."
                return state
            summary = self._format_memory_preview(key, memory_value)
            state.context["command_result"] = summary
            return state

        # No specific key; provide list summary
        summaries = []
        for idx, (key, value) in enumerate(memories.items()):
            summaries.append(self._format_memory_preview(key, value, include_details=False))
            if idx >= 9:
                summaries.append("... (showing first 10 memories)")
                break

        state.context["command_result"] = "\n".join(summaries)
        return state

    def _command_delete(self, state: AgentState) -> AgentState:
        command_arg = state.context.get("command_arg")
        if not command_arg:
            state.context["command_result"] = "Please specify which memory to delete. Usage: /delete <memory_key>."
            return state

        if not state.user_id:
            state.context["command_result"] = "Cannot delete memory: user not authenticated."
            return state

        key = command_arg.strip()
        db_session = db_manager.get_session()
        try:
            deleted_count = (
                db_session.query(DBMemory)
                .filter(DBMemory.user_id == state.user_id, DBMemory.key == key)
                .delete()
            )
            db_session.commit()

            if deleted_count:
                state.context["command_result"] = f"Memory '{key}' deleted."
                state.long_term_memory.pop(key, None)
            else:
                state.context["command_result"] = f"Memory '{key}' not found."
        except Exception as e:
            state.context["command_result"] = f"Failed to delete memory '{key}': {str(e)}"
        finally:
            db_session.close()

        return state

    def _command_clear(self, state: AgentState) -> AgentState:
        state.context["needs_clear_confirmation"] = True
        state.context["command_result"] = (
            "You are requesting to clear ALL memories. Please confirm with '/clear confirm' to proceed."
        )

        command_arg = state.context.get("command_arg", "").lower()
        if command_arg == "confirm":
            if not state.user_id:
                state.context["command_result"] = "Cannot clear memories: user not authenticated."
                state.context.pop("needs_clear_confirmation", None)
                return state

            db_session = db_manager.get_session()
            try:
                deleted_count = (
                    db_session.query(DBMemory)
                    .filter(DBMemory.user_id == state.user_id)
                    .delete()
                )
                db_session.commit()
                state.long_term_memory = {}
                state.context["command_result"] = (
                    f"All memories cleared ({deleted_count} deleted)."
                )
            except Exception as e:
                state.context["command_result"] = f"Failed to clear memories: {str(e)}"
            finally:
                db_session.close()

            state.context.pop("needs_clear_confirmation", None)

        return state

    def _command_help(self, state: AgentState) -> AgentState:
        """Show available commands and their descriptions"""
        help_text = """
🤖 **AxiomOS Available Commands:**

**/save** - Save current conversation to long-term memory
  Usage: /save
  
**/recall** - Retrieve saved memories from long-term memory
  Usage: /recall [memory_key]
  Examples: /recall (shows all memories)
           /recall memory_20231201_143022 (shows specific memory)
  
**/delete** - Delete a specific memory from long-term memory
  Usage: /delete <memory_key>
  Example: /delete memory_20231201_143022
  
**/clear** - Clear all memories from long-term memory
  Usage: /clear (shows confirmation)
         /clear confirm (executes the clear operation)
  ⚠️ This action cannot be undone!

**/help** - Show this help message
  Usage: /help

💡 **Tips:**
- Memories are stored with timestamps as keys
- Use /recall first to see available memory keys
- /save preserves your conversation context for future reference
- All memory operations require user authentication
        """.strip()
        
        state.context["command_result"] = help_text
        return state

    def _format_memory_preview(self, key: str, value: Any, include_details: bool = True) -> str:
        try:
            if isinstance(value, str):
                parsed = json.loads(value)
            else:
                parsed = value
        except Exception:
            parsed = value

        if isinstance(parsed, dict):
            meta = []
            if "created_by" in parsed:
                meta.append(f"created_by={parsed['created_by']}")
            if "context" in parsed and isinstance(parsed["context"], dict):
                meta.append(f"context_keys={len(parsed['context'])}")

            messages = parsed.get("messages", [])
            snippet = ""
            if messages:
                first_msg = messages[0]
                if isinstance(first_msg, dict):
                    content = first_msg.get("content") or str(first_msg)
                else:
                    content = str(first_msg)
                snippet = content[:120]

            base = f"{key}: {snippet}" if snippet else f"{key}: [no preview]"
            if include_details and meta:
                base += f" ({', '.join(meta)})"
            return base

        # Fallback for non-dict values
        return f"{key}: {str(value)[:120]}"

    @traceable
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

    @traceable
    def _process_message(self, state: AgentState) -> AgentState:
        """Process messages and detect commands"""
        if not state.messages:
            return state

        last_message = state.messages[-1]

        # Reset per-request command flags (they may persist in Redis session context)
        for flag in (
            "processing_remember",
            "processing_recall",
            "processing_delete",
            "command",
            "command_arg",
            "skip_llm_response",
            "command_result",
        ):
            state.context.pop(flag, None)

        message_text = last_message.strip()

        # Detect slash commands (/save, /recall, /delete, /clear)
        if message_text.startswith("/") and len(message_text) > 1:
            parts = message_text[1:].split(maxsplit=1)
            command = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""
            state.context["command"] = command
            if arg:
                state.context["command_arg"] = arg
            return state

        # Detect legacy keywords for backwards compatibility (no slash)
        lowered = message_text.lower()
        if "remember" in lowered:
            state.context["processing_remember"] = True
        elif "recall" in lowered:
            state.context["processing_recall"] = True
        elif "delete" in lowered and ("memory" in lowered or "memories" in lowered):
            state.context["processing_delete"] = True

        return state

    @traceable
    def _save_memory(self, state: AgentState) -> AgentState:
        """Save memory to Redis and PostgreSQL"""
        # Save session context to Redis (omit ephemeral keys)
        if state.session_id and state.context:
            ephemeral_keys = {
                "command_result",
                "skip_llm_response",
                "skip_memory_save",
                "needs_clear_confirmation",
                "command",
                "command_arg",
            }
            sanitized_context = {
                key: value
                for key, value in state.context.items()
                if key not in ephemeral_keys
            }
            redis_manager.set_session_data(
                state.session_id, {"context": sanitized_context}, ttl=config.session_timeout
            )

        # Never create new memories on a deletion request or when explicitly skipped.
        if state.context.get("processing_delete") or state.context.get("skip_memory_save"):
            state.context.pop("skip_memory_save", None)
            return state

        # Auto-save is disabled - session data is handled by Redis above
        # Only explicit remember commands should save to long-term memory

        # Save important data to long-term memory (explicit remember command)
        if state.user_id and state.context.get("processing_remember"):
            db_session = db_manager.get_session()
            try:
                memory_key = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                # Save all messages, not just the last 5, and include single messages
                memory_value = {
                    "messages": state.messages if len(state.messages) > 0 else [],
                    "context": state.context,
                    "explicitly_saved": True,
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
            
            # Check for explicit "delete all" patterns first
            delete_all_patterns = [
                "delete all memories", "clear all memories", "remove everything",
                "delete all", "clear memories", "remove all memories",
                "delete everything", "clear all", "remove all"
            ]
            
            user_request_lower = last_message.lower()
            is_explicit_delete_all = any(pattern in user_request_lower for pattern in delete_all_patterns)
            
            if is_explicit_delete_all:
                return self._execute_delete_all(state, memories)

            # Prompt Groq to decide about deletion for specific cases
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
            if decision == "DELETE_ALL" or decision.startswith("DELETE_ALL:"):
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
                
                # Clear the agent's long_term_memory state to reflect deletion
                state.long_term_memory = {}
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
                    # Remove the deleted memory from the agent's state
                    if memory_key in state.long_term_memory:
                        del state.long_term_memory[memory_key]
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

    @traceable(name="axiom_agent_respond")
    def _respond(self, state: AgentState) -> AgentState:
        """Generate intelligent response using Groq"""
        if not state.messages:
            return state

        last_message = state.messages[-1]

        # Optionally enrich context with web search when permitted
        state = self._maybe_add_web_results(state, last_message)

        # Handle command responses without calling the LLM
        if state.context.get("skip_llm_response"):
            response = state.context.get(
                "command_result", "Command executed."
            )
            if response and isinstance(response, str):
                state.messages.append(response)

            # Clean ephemeral flags
            state.context.pop("skip_llm_response", None)
            state.context.pop("command_result", None)
            state.context.pop("needs_clear_confirmation", None)
            return state

        # Use Groq for intelligent responses
        try:
            # Build conversation context
            conversation_context = []

            # High-level instruction so the model understands web search behaviour
            system_instruction = (
                "You are AxiomOS, a personal assistant. "
                "If system messages include 'Recent web search results (Tavily):', "
                "you DO have access to those up-to-date web search results. "
                "Use them as the primary source for current factual questions, and do NOT say that you lack web "
                "access or browsing. Instead, base your answer on those results and your general knowledge."
            )
            conversation_context.append({"role": "system", "content": system_instruction})

            # Add long-term memories as context
            if state.long_term_memory:
                memory_keys = list(state.long_term_memory.keys())[:5]
                memory_summary = f"User's long-term memories: {memory_keys}"
                conversation_context.append(
                    {"role": "system", "content": memory_summary}
                )

            # Add web search context if available
            web_results = state.context.get("web_search_results")
            if web_results:
                conversation_context.append(
                    {
                        "role": "system",
                        "content": f"Recent web search results (Tavily):\n{web_results}",
                    }
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

            # Handle legacy keyword commands (non-slash)
            if state.context.get("processing_delete"):
                delete_result = state.context.get(
                    "delete_result", "Memory deletion request processed."
                )
                response = f"{delete_result}"
            elif state.context.get("processing_recall"):
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
                                                    role = msg.get("role", "unknown")
                                                    content = msg.get("content", "")
                                                    msg_texts.append(f'{role}: "{content}"')
                                                elif isinstance(msg, dict) and "role" in msg:
                                                    # Handle different message formats
                                                    role = msg.get("role", "unknown")
                                                    msg_content = str(msg.get("content", msg))
                                                    msg_texts.append(f'{role}: "{msg_content}"')
                                                else:
                                                    msg_texts.append(f'"{str(msg)}"')
                                            
                                            # Create a readable summary
                                            if len(msg_texts) > 3:
                                                preview = "; ".join(msg_texts[:2]) + f"; ... (+{len(msg_texts)-2} more)"
                                            else:
                                                preview = "; ".join(msg_texts)
                                            
                                            memory_content.append(
                                                f"Memory '{key}': {preview}"
                                            )
                                        else:
                                            memory_content.append(
                                                f"Memory '{key}': [empty conversation]"
                                            )
                                    else:
                                        memory_content.append(
                                            f"Memory '{key}': {str(value)[:200]}..."
                                        )
                                except json.JSONDecodeError:
                                    memory_content.append(f"Memory '{key}': {value}")
                            else:
                                memory_content.append(f"Memory '{key}': {str(value)[:200]}...")
                        except Exception as e:
                            memory_content.append(
                                f"Memory '{key}': Error reading content - {e}"
                            )

                    if memory_content:
                        memory_info = (
                            "\n\nHere's what I remember about you:\n"
                            + "\n".join(memory_content)
                        )
                    else:
                        memory_info = (
                            "\n\nI found memories but couldn't extract their content."
                        )
                else:
                    memory_info = "\n\nI don't have any memories stored about you."

                response += memory_info
            elif state.context.get("processing_remember"):
                response = "I've saved our conversation to your long-term memory."

        except Exception as e:
            response = f"I received your message: '{last_message}'. I'm AxiomOS, your personal assistant. (Note: Groq API error: {str(e)})"

        if response and isinstance(response, str):
            state.messages.append(response)

        # Clear transient flags after response
        for flag in (
            "processing_delete",
            "processing_recall",
            "processing_remember",
            "delete_result",
            "skip_memory_save",
        ):
            state.context.pop(flag, None)

        return state

    @traceable(name="axiom_agent_run_stream")
    async def run_stream(self, request: AgentRequestModel) -> TokenStream:
        """Run agent with streaming response"""
        initial_state = AgentState(
            session_id=request.session_id, messages=[request.message]
        )

        if request.allow_web_search:
            initial_state.context["allow_web_search"] = True

        # Process through simple, reliable workflow
        state = self._authenticate(initial_state)
        state = self._load_memory(state)
        state = self._process_message(state)
        state = self._execute_command(state)

        # If command handled the response, bypass streaming LLM
        if state.context.get("skip_llm_response"):
            response = state.context.get("command_result", "Command executed.")
            yield StreamChunkModel(
                token=response,
                session_id=state.session_id,
                is_complete=True,
                final_response=response,
            )
            state.context.pop("skip_llm_response", None)
            state.context.pop("command_result", None)
            state.context.pop("needs_clear_confirmation", None)
            state.context.pop("skip_memory_save", None)
            state.messages.append(response)
            state = self._save_memory(state)
            return

        # Optionally enrich context with web search when permitted
        if request.message:
            state = self._maybe_add_web_results(state, request.message)

        # Now stream the response
        try:
            # Build conversation context for streaming
            conversation_context = []

            system_instruction = (
                "You are AxiomOS, a personal assistant. "
                "If system messages include 'Recent web search results (Tavily):', "
                "you DO have access to those up-to-date web search results. "
                "Use them as the primary source for current factual questions, and do NOT say that you lack web "
                "access or browsing. Instead, base your answer on those results and your general knowledge."
            )
            conversation_context.append({"role": "system", "content": system_instruction})

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

            web_results = state.context.get("web_search_results")
            if web_results:
                conversation_context.append(
                    {
                        "role": "system",
                        "content": f"Recent web search results (Tavily):\n{web_results}",
                    }
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
            state = self._save_memory(state)

            # Clear transient flags to keep context tidy
            for flag in (
                "processing_delete",
                "processing_recall",
                "processing_remember",
                "delete_result",
                "skip_memory_save",
            ):
                state.context.pop(flag, None)

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
