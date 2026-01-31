import chainlit as cl
from typing import Optional
import asyncio

from src.agent import axiom_agent
from src.models import AgentRequestModel, StreamChunkModel
from src.config import config


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    # Send welcome message
    await cl.Message(
        content="🤖 **AxiomOS** - Personal Assistant for Organizing Your Life\n\n"
        "I'm here to help you with intelligent conversations and remember important information. "
        "Type `remember` followed by something you want me to save, or `recall` to retrieve memories.\n\n"
        "I'm powered by Groq's fast LLM models and have both session and long-term memory capabilities.",
        author="AxiomOS",
    ).send()

    # Initialize session data
    cl.user_session.set("session_id", None)
    cl.user_session.set("message_count", 0)


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages with streaming response"""
    try:
        # Get or create session ID
        session_id = cl.user_session.get("session_id")
        message_count = cl.user_session.get("message_count", 0)

        # Create request
        request = AgentRequestModel(
            message=message.content, session_id=session_id, stream=True
        )

        # Create a streaming message
        msg = cl.Message(content="", author="AxiomOS")
        await msg.send()

        # Stream the response
        full_response = ""
        async for chunk in axiom_agent.run_stream(request):
            if chunk.token:
                full_response += chunk.token
                await msg.stream_token(chunk.token)

            if chunk.is_complete:
                # Update session ID if this is the first message
                if not session_id:
                    cl.user_session.set("session_id", chunk.session_id)

                # Update message count
                cl.user_session.set("message_count", message_count + 1)

                # Add memory context if applicable
                if "remember" in message.content.lower():
                    memory_note = "\n\n💾 *I've saved this conversation to your long-term memory.*"
                    await msg.stream_token(memory_note)
                elif "recall" in message.content.lower():
                    memory_note = f"\n\n*Retrieved from your memory banks.*"
                    await msg.stream_token(memory_note)

                # Finalize the message
                await msg.update()
                break

    except Exception as e:
        # Handle errors
        error_msg = cl.Message(
            content=f"Sorry, I encountered an error: {str(e)}\n\n"
            f"Please try again or check if the services are running properly.",
            author="AxiomOS",
        )
        await error_msg.send()


@cl.on_settings_update
async def setup_agent(settings: dict):
    """Update agent settings from UI"""
    # Update configuration based on user settings
    if "model" in settings:
        config.groq.model = settings["model"]

    if "temperature" in settings:
        config.groq.temperature = float(settings["temperature"])

    if "max_tokens" in settings:
        config.groq.max_tokens = int(settings["max_tokens"])

    await cl.Message(
        content=f"⚙️ Settings updated:\n"
        f"- Model: {config.groq.model}\n"
        f"- Temperature: {config.groq.temperature}\n"
        f"- Max Tokens: {config.groq.max_tokens}",
        author="AxiomOS",
    ).send()


@cl.action_callback("show_memory")
async def show_memory(action: cl.Action):
    """Show user's long-term memory"""
    session_id = cl.user_session.get("session_id")
    if not session_id:
        await cl.Message(
            content="No active session. Start a conversation first.", author="AxiomOS"
        ).send()
        return

    try:
        # Get session data from Redis
        from src.redis_manager import redis_manager

        session_data = redis_manager.get_session_data(session_id)

        if session_data and session_data.get("context"):
            context = session_data["context"]
            memory_info = "🧠 **Session Memory:**\n\n"

            for key, value in context.items():
                memory_info += f"- **{key}:** {value}\n"

            await cl.Message(content=memory_info, author="AxiomOS").send()
        else:
            await cl.Message(
                content="No session memory found.", author="AxiomOS"
            ).send()

    except Exception as e:
        await cl.Message(
            content=f"Error retrieving memory: {str(e)}", author="AxiomOS"
        ).send()


@cl.action_callback("clear_session")
async def clear_session(action: cl.Action):
    """Clear the current session"""
    session_id = cl.user_session.get("session_id")

    if session_id:
        try:
            from src.redis_manager import redis_manager

            redis_manager.delete_session(session_id)

            # Reset session data
            cl.user_session.set("session_id", None)
            cl.user_session.set("message_count", 0)

            await cl.Message(
                content="🗑️ Session cleared. Starting fresh!", author="AxiomOS"
            ).send()

        except Exception as e:
            await cl.Message(
                content=f"Error clearing session: {str(e)}", author="AxiomOS"
            ).send()
    else:
        await cl.Message(content="No active session to clear.", author="AxiomOS").send()


@cl.action_callback("help")
async def show_help(action: cl.Action):
    """Show help information"""
    help_content = """
    🤖 **AxiomOS Help**
    
    **Commands:**
    - `remember <information>` - Save information to long-term memory
    - `recall` - Retrieve information from memory
    - Regular conversation - I'll respond intelligently using Groq
    
    **Features:**
    - 🧠 Long-term memory storage
    - 💬 Session continuity
    - ⚡ Fast responses via Groq
    - 🔄 Streaming token-by-token output
    
    **Actions:**
    - Use the action buttons below to manage memory and sessions
    
    **Settings:**
    - Adjust model parameters in the settings panel
    
    I'm here to help with intelligent conversations and remember important information!
    """

    await cl.Message(content=help_content, author="AxiomOS").send()


# Add action buttons to the UI
@cl.on_chat_end
async def on_chat_end():
    """Clean up when chat ends"""
    session_id = cl.user_session.get("session_id")
    if session_id:
        try:
            from src.redis_manager import redis_manager

            redis_manager.delete_session(session_id)
        except:
            pass


# Register action buttons
@cl.on_settings_update
async def setup_actions(settings: dict):
    """Setup action buttons"""
    actions = [
        cl.Action(
            id="show_memory",
            name="Show Memory",
            description="View current session memory",
            icon="🧠",
        ),
        cl.Action(
            id="clear_session",
            name="Clear Session",
            description="Clear current session data",
            icon="🗑️",
        ),
        cl.Action(
            id="help", name="Help", description="Show help information", icon="❓"
        ),
    ]

    await cl.Message(content="", actions=actions, author="AxiomOS").send()


# Configuration is now handled in .chainlit/config.toml or through the UI
