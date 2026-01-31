import logging
from typing import AsyncGenerator, List
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from .chat_message import ChatMessage, ChatRole
from .agent_state import AgentState
from ..config import config

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.groq_client = ChatGroq(
            api_key=config.groq.api_key,
            model=config.groq.model,
            temperature=config.groq.temperature,
            max_tokens=config.groq.max_tokens,
        )

    async def generate_response(self, messages: List[ChatMessage]) -> str:
        if not messages:
            return "No messages to process"

        try:
            langchain_messages = self._convert_to_langchain_format(messages)
            response = self.groq_client.invoke(langchain_messages)

            if response is not None and hasattr(response, "content"):
                content = str(response.content) if response.content is not None else ""
            else:
                content = str(response) if response else ""

            self.logger.debug(f"Generated response: {len(content)} characters")
            return content

        except Exception as e:
            self.logger.error(f"Groq API error: {e}")
            last_message = messages[-1] if messages else ""
            message_content = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )
            return f"I received your message: '{message_content}'. I'm AxiomOS, your personal assistant. (Note: Groq API error: {str(e)})"

    async def generate_response_stream(
        self, messages: List[ChatMessage]
    ) -> AsyncGenerator[str, None]:
        if not messages:
            yield "No messages to process"
            return

        try:
            langchain_messages = self._convert_to_langchain_format(messages)
            chat_stream = self.groq_client.stream(langchain_messages)

            for chunk in chat_stream:
                if (
                    chunk is not None
                    and hasattr(chunk, "content")
                    and chunk.content is not None
                ):
                    token = str(chunk.content)
                    self.logger.debug(f"Streamed token: {repr(token)}")
                    yield token

        except Exception as e:
            self.logger.error(f"Groq streaming error: {e}")
            last_message = messages[-1] if messages else None
            if last_message and hasattr(last_message, "content"):
                message_content = (
                    last_message.content if last_message.content is not None else ""
                )
            else:
                message_content = str(last_message) if last_message else ""
            fallback = f"I received your message: '{message_content}'. I'm AxiomOS, your personal assistant. (Note: Groq streaming error: {str(e)})"
            yield fallback

    def _convert_to_langchain_format(self, messages: List[ChatMessage]):
        langchain_messages = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                if msg.role == ChatRole.SYSTEM:
                    langchain_messages.append(SystemMessage(content=msg.content))
                elif msg.role == ChatRole.USER:
                    langchain_messages.append(HumanMessage(content=msg.content))
                elif msg.role == ChatRole.ASSISTANT:
                    langchain_messages.append(
                        HumanMessage(content=f"Assistant: {msg.content}")
                    )
            else:
                # Handle legacy string messages
                langchain_messages.append(HumanMessage(content=str(msg)))

        return langchain_messages

    async def process_with_commands(self, state: AgentState) -> AgentState:
        if not state.messages:
            return state

        last_message = state.messages[-1]

        # Prepare messages for LLM
        messages_for_llm = []

        # Add system message about long-term memory if available
        if state.long_term_memory:
            memory_keys = list(state.long_term_memory.keys())[:5]
            memory_summary = f"User's long-term memories: {memory_keys}"
            messages_for_llm.append(ChatMessage.system_message(memory_summary))

        # Add conversation history (last 3 messages before current)
        if len(state.messages) > 1:
            for msg in state.messages[-4:-1]:  # Last 4 excluding current
                messages_for_llm.append(msg)

        # Add current message
        messages_for_llm.append(last_message)

        # Generate response
        response = await self.generate_response(messages_for_llm)

        # Handle special commands
        if "recall" in state.detected_commands:
            memory_info = "\n\nAvailable memories: " + str(
                list(state.long_term_memory.keys())
            )
            response += memory_info
        elif "remember" in state.detected_commands:
            response = "I've saved our conversation to your long-term memory."

        # Add response to state
        response_message = ChatMessage.assistant_message(response)
        updated_state = state.with_message(response_message)

        self.logger.debug(f"Processed message with commands: {state.detected_commands}")

        return updated_state
