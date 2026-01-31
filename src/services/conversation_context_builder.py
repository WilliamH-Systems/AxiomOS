import logging
import re
from typing import List, Optional

from .chat_message import ChatMessage, ChatRole
from .command_types import CommandType
from .agent_state import AgentState

logger = logging.getLogger(__name__)


class CommandDetector:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.command_patterns = {
            CommandType.REMEMBER: [
                # direct imperatives with clear object
                r"\bremember\s+(this|that|it)\b",
                r"\bremember\s+(this|that|it)\s*(for\s+later|for\s+next\s+time|when\s+I\s+ask|next\s+time)?\b",
                r"\bplease\s+remember\s+(this|that|it)\b",
                r"\bcan\s+you\s+remember\s+(this|that|it)\b",
                r"\bcould\s+you\s+remember\s+(this|that|it)\b",
                r"\btry\s+to\s+remember\s+(this|that|it)\b",
                
                # “don’t forget” → remember (imperative)
                r"\bdon['’]t\s+forget\s+(this|that|it)\b",
                r"\bdo\s+not\s+forget\s+(this|that|it)\b",
                r"\bdon['’]t\s+forget\s+about\s+(this|that|it)\b",
                r"\bdo\s+not\s+forget\s+about\s+(this|that|it)\b",
                
                # save/store phrasing with explicit object
                r"\bsave\b.*\b(conversation|this|that|it)\b",
                r"\bplease\s+save\b.*\b(conversation|this|that|it)\b",
                r"\bcan\s+you\s+save\b.*\b(conversation|this|that|it)\b",
                r"\bstore\b.*\b(memory|this|that|it)\b",
                r"\bput\s+(this|that|it)\s+in\s+memory\b",
                r"\badd\s+(this|that|it)\s+to\s+your\s+memory\b",
                
                # “keep this in mind” style
                r"\bkeep\s+(this|that|it)\s+in\s+mind\b",
                r"\bplease\s+keep\s+(this|that|it)\s+in\s+mind\b",
                r"\bcan\s+you\s+keep\s+(this|that|it)\s+in\s+mind\b",
                r"\bhold\s+on\s+to\s+(this|that|it)\b",
                r"\bkeep\s+track\s+of\s+(this|that|it)\b",
                r"\bkeep\s+(this|that|it)\s+for\s+later\b",
                r"\bcan\s+you\s+keep\s+(this|that|it)\s+for\s+later\b",
                r"\bcould\s+you\s+keep\s+(this|that|it)\s+for\s+later\b",
                
                # “make a note” phrasing
                r"\bmake\s+a\s+note\s+of\s+(this|that|it)\b",
                r"\bplease\s+make\s+a\s+note\s+of\s+(this|that|it)\b",
                r"\bnote\s+(this|that|it)\s+for\s+later\b",
                
                # meta‑instructions about upcoming or just‑said content
                r"\bremember\s+what\s+I\s+just\s+said\b",
                r"\bremember\s+what\s+I\s+am\s+about\s+to\s+say\b",
                r"\bremember\s+the\s+following\b",
                r"\bremember\s+this\s+information\b",
                r"\bremember\s+this\s+detail\b",
                r"\bremember\s+this\s+message\b",
                r"\bremember\s+this\s+note\b",
                r"\bremember\s+this\s+for\s+me\b",
                
                # explicit user intent directed at the agent
                r"\bI\s+need\s+you\s+to\s+remember\s+(this|that|it)\b",
                r"\bI\s+want\s+you\s+to\s+remember\s+(this|that|it)\b",
                r"\bI\s+need\s+you\s+to\s+remember\b.*\b(for\s+later|next\s+time)\b",
                r"\bI\s+want\s+you\s+to\s+remember\b.*\b(for\s+later|next\s+time)\b",
                
                # “commit to memory” / “store away”
                r"\bcommit\s+(this|that|it)\s+to\s+memory\b",
                r"\bstore\s+(this|that|it)\s+away\b",
                
                # “put this” → remember (must explicitly reference memory)
                r"\bput\s+(this|that|it)\s+(in|into)\s+(your\s+)?memory\b",
                r"\bput\s+(this|that|it)\s+to\s+memory\b",
                r"\bput\s+(this|that|it)\s+in\s+your\s+long[-\s]*term\s+memory\b",
                r"\bput\s+(this|that|it)\s+away\s+in\s+memory\b",
                r"\bput\s+(this|that|it)\s+aside\s+for\s+later\b",
            ],

            CommandType.RECALL: [
                # direct recall commands
                r"\brecall\b",
                r"\bplease\s+recall\b",
                r"\bcan\s+you\s+recall\b",
                r"\bcould\s+you\s+recall\b",

                # “what do you remember”
                r"\bwhat\s+do\s+you\s+remember\b",
                r"\bwhat\s+can\s+you\s+remember\b",

                # “do you remember anything / do you remember X”
                r"\bdo\s+you\s+remember\b.*",
                r"\bcan\s+you\s+remember\b.*",
                r"\bcould\s+you\s+remember\b.*",

                # “tell me about your memory”
                r"\btell\s+me\s+about\b.*\b(memory|memories)\b",
                r"\btell\s+me\s+what\s+you\s+remember\b",

                # “show me what you remember”
                r"\bshow\s+me\s+what\s+you\s+remember\b",
                r"\bshow\s+me\b.*\b(memory|memories)\b",
                r"\bshow\b.*\b(what\s+you\s+remember|your\s+memories)\b",

                # “what do you recall”
                r"\bwhat\s+do\s+you\s+recall\b",
                r"\bwhat\s+can\s+you\s+recall\b",
                
                # “give me your memory of…”
                r"\bgive\s+me\s+(your\s+)?(memory|memories)\b.*",
                r"\bgive\s+me\s+what\s+you\s+remember\b",

                # “remind me what you remember”
                r"\bremind\s+me\s+what\s+you\s+remember\b",
            ],


            CommandType.HELP: [
                r"\bhelp\b",
                r"\bwhat\s+can\s+you\s+do\b",
                r"\bcommands?\b",
                r"\bshow\b.*\bhelp\b",
            ],

            CommandType.CLEAR: [
                r"\bclear\b",
                r"\breset\b",
                r"\bstart\s+over\b",
                r"\bclear\s+(context|conversation|memory)\b",
            ],
        }

    def detect_commands(self, message: str) -> List[str]:
        if not message:
            return []

        detected = []
        message_lower = message.lower()

        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    detected.append(command_type.value)
                    break  # Only add each command type once

        if detected:
            self.logger.debug(f"Detected commands: {detected}")

        return detected


class ConversationContextBuilder:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.command_detector = CommandDetector()

    def build_conversation_context(
        self,
        current_message: ChatMessage,
        message_history: List[ChatMessage],
        long_term_memory: dict,
        max_history: int = 3,
    ) -> List[ChatMessage]:
        context_messages = []

        # Add system context about long-term memory
        if long_term_memory:
            memory_keys = list(long_term_memory.keys())[:5]
            memory_summary = f"User's long-term memories: {memory_keys}"
            context_messages.append(ChatMessage.system_message(memory_summary))
            self.logger.debug(f"Added memory context with {len(memory_keys)} keys")

        # Add recent conversation history (excluding current message)
        if len(message_history) > 1:
            recent_messages = message_history[
                -(max_history + 1) : -1
            ]  # Last N messages before current
            for msg in recent_messages:
                if msg.role != ChatRole.SYSTEM:  # Skip system messages in history
                    context_messages.append(msg)
            self.logger.debug(f"Added {len(recent_messages)} historical messages")

        # Add current message
        context_messages.append(current_message)

        return context_messages

    def detect_and_set_commands(self, state: AgentState) -> AgentState:
        if not state.messages:
            return state

        last_message = state.messages[-1]
        message_content = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

        detected_commands = self.command_detector.detect_commands(message_content)

        # Update context based on detected commands
        updated_context = dict(state.context)

        if CommandType.REMEMBER.value in detected_commands:
            updated_context["processing_remember"] = True
            self.logger.debug("Set processing_remember flag")

        if CommandType.RECALL.value in detected_commands:
            updated_context["processing_recall"] = True
            self.logger.debug("Set processing_recall flag")

        if CommandType.CLEAR.value in detected_commands:
            updated_context["clear_context"] = True
            self.logger.debug("Set clear_context flag")

        # Update state with detected commands and context
        updated_state = state.with_detected_commands(detected_commands)
        updated_state = updated_state.with_context(**updated_context)

        return updated_state

    def create_help_response(self) -> str:
        return """
I'm AxiomOS, your personal assistant. Here are some commands you can use:

• **remember** - Save our current conversation to your long-term memory
• **recall** - Show what I remember from our past conversations
• **help** - Display this help message
• **clear** - Clear the current conversation context

You can also just chat with me naturally! I'll remember our conversation context within this session.
        """.strip()

    def should_handle_as_command(self, state: AgentState) -> bool:
        if not state.detected_commands:
            return False

        # Check for commands that should be handled immediately
        immediate_commands = [CommandType.HELP.value, CommandType.CLEAR.value]

        for cmd in state.detected_commands:
            if cmd in immediate_commands:
                return True

        return False

    def handle_immediate_command(self, state: AgentState) -> AgentState:
        if not state.detected_commands:
            return state

        response_content = None

        if CommandType.HELP.value in state.detected_commands:
            response_content = self.create_help_response()

        elif CommandType.CLEAR.value in state.detected_commands:
            response_content = "Conversation context cleared. How can I help you?"
            # Clear context but keep long-term memory
            state = state.with_context()

        if response_content:
            response_message = ChatMessage.assistant_message(response_content)
            state = state.with_message(response_message)
            self.logger.info(f"Handled immediate command: {state.detected_commands}")

        return state
