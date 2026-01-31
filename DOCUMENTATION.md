# Complete Architecture Documentation

## Overview
This document describes the architecture, separated concerns, and proper abstractions.

## Architecture Principles

### 1. Separation of Concerns
Each service has a single, well-defined responsibility:
- **SessionService**: Authentication and session lifecycle
- **MemoryService**: Session (Redis) and long-term (PostgreSQL) memory
- **LLMService**: Groq API communication and response generation
- **ConversationContextBuilder**: Context building and command detection

### 2. Dependency Injection
The main agent accepts services via constructor injection:
```python
agent = AxiomOSAgent(
    session_service=custom_session_service,
    memory_service=custom_memory_service,
    llm_service=custom_llm_service,
    context_builder=custom_context_builder
)
```

### 3. Immutable State
AgentState is immutable using `@dataclass(frozen=True)`:
```python
state = state.with_user_id(123)
state = state.with_message(ChatMessage.user_message("hello"))
state = state.with_context(theme="dark_mode")
```

### 4. Structured Communication
Replaced raw strings with ChatMessage objects:
```python
message = ChatMessage.user_message("Hello", metadata={"source": "web"})
response = ChatMessage.assistant_message("Hi there!")
```

## Service Details

### SessionService
- **Purpose**: Authentication and session management
- **Responsibilities**:
  - Create/validate sessions in PostgreSQL
  - Handle session expiration and extension
  - Fallback to default user when DB unavailable
- **Methods**: `authenticate_or_create_session()`, `extend_session()`, `validate_session()`

### MemoryService
- **Purpose**: Memory management across Redis and PostgreSQL
- **Responsibilities**:
  - Session memory in Redis (fast access, TTL-based)
  - Long-term memory in PostgreSQL (persistent, JSON-serialized)
  - Normalized JSON deserialization on load
- **Methods**: `load_all_memory()`, `save_all_memory()`, `save_conversation_memory()`

### LLMService
- **Purpose**: Groq API interactions and response generation
- **Responsibilities**:
  - Convert ChatMessage objects to LangChain format
  - Handle both streaming and non-streaming responses
  - Process command-specific response modifications
- **Methods**: `generate_response()`, `generate_response_stream()`, `process_with_commands()`

### ConversationContextBuilder
- **Purpose**: Centralized context building and command detection
- **Responsibilities**:
  - Detect commands using regex patterns
  - Build conversation context from history and memory
  - Handle immediate commands (help, clear)
- **Methods**: `detect_and_set_commands()`, `build_conversation_context()`

## Data Flow

### Non-Streaming Flow:
1. **Authenticate** → SessionService validates/creates session
2. **Load Memory** → MemoryService loads Redis + PostgreSQL data
3. **Process Commands** → ConversationContextBuilder detects commands
4. **Save Memory** → MemoryService persists session changes
5. **Respond** → LLMService generates response using context

### Streaming Flow:
1-4. Same as non-streaming
5. **Stream Response** → LLMService streams tokens directly
6. **Finalize** → Save complete response to memory

## I have...

### 1. Eliminated Code Duplication
- **Before**: Conversation context building duplicated in `run()` and `run_stream()`
- **After**: Single `build_conversation_context()` method in ConversationContextBuilder

### 2. Improved Error Handling
- **Before**: Inconsistent exception handling with print statements
- **After**: Structured logging with proper fallback behavior

### 3. Better Testability
- **Before**: Monolithic class difficult to unit test
- **After**: Each service independently testable with dependency injection

### 4. Enhanced Memory Management
- **Before**: Inconsistent JSON handling, mixed memory storage
- **After**: Normalized JSON serialization/deserialization, clear separation

### 5. Improved Command Processing
- **Before**: Simple string contains checks
- **After**: Regex-based pattern matching, immediate command handling

### Overview
- Structured logging with configurable levels
- Service-specific log filtering
- Comprehensive error logging with context

## Future Extensibility

### Adding New Commands:
1. Add to `CommandType` enum
2. Update command patterns in `CommandDetector`
3. Handle in appropriate service or ConversationContextBuilder

### Adding New Memory Backends:
1. Extend MemoryService with new methods
2. Use dependency injection for custom implementation
3. Maintain same interface for compatibility

### Adding New LLM Providers:
1. Create new service implementing same interface
2. Inject into agent constructor
3. Ensure proper ChatMessage conversion

## Testing

Run the comprehensive test suite:
```bash
python test_refactored_agent.py
```

Tests cover:
- Basic message processing
- Command detection and handling
- Streaming functionality  
- Memory operations
- Error handling and fallbacks

## Performance Considerations

### Memory Optimization:
- Redis for session data (fast, TTL-managed)
- PostgreSQL for long-term memory (persistent, indexed)
- Lazy loading of memory data only when needed

### Response Time:
- Parallel service execution where possible
- Early return for immediate commands
- Efficient context building with limits

### Resource Management:
- Proper database session cleanup with try/finally
- Connection pooling via SQLAlchemy
- Redis connection management

## Security Considerations

- All inputs validated with Pydantic models
- Database operations use parameterized queries
- Session data properly isolated by user_id
- Sensitive configuration via environment variables
- Comprehensive logging for monitoring

## Summary

1. **Clean Separation**: Each service has focused responsibility
2. **No Duplication**: Single source of truth for each operation  
3. **Structured Data**: ChatMessage objects replace raw strings
4. **Immutable State**: Safe concurrent operations with dataclass.replace
5. **Better Commands**: Regex-based detection with immediate handling
6. **Improved Streaming**: Final responses appended once
7. **Dependency Injection**: Testable, flexible architecture
8. **Proper Logging**: Structured, configurable logging throughout

AxiomOS provides a foundation for future enhancements and production deployment.