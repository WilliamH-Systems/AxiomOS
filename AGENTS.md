# AxiomOS - Agent Development Guidelines

This file contains guidelines and commands for agentic coding agents working in the AxiomOS repository.

## Project Overview

AxiomOS is a Python project using modern Python 3.13+ with pyproject.toml for configuration. The project follows standard Python conventions and uses a virtual environment for dependency management. MAKE SURE TO ACTIVATE THE VIRTUAL ENVIRONMENT BEFORE INSTALLING PACKAGES. When installing packages, use "uv add", not "pip install" or "uv pip".

## Build/Lint/Test Commands

### Running Tests
```bash
# Run all integration tests
python test_integration.py

# Run database tests
python test_database.py

# Run workflow tests
python test_workflow.py

# Run specific test by function name (modify test file to call specific function)
python -c "from test_database import test_database; test_database()"
```

### Running the Application
```bash
# FastAPI backend only
python fastapi_app.py

# Chainlit UI only
chainlit run chainlit_app.py

# Both services (recommended - run in separate terminals)
python fastapi_app.py     # Terminal 1
chainlit run chainlit_app.py    # Terminal 2

# CLI interface
python main.py
```

### Development Commands
```bash
# Install new dependencies
uv add <package_name>

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Database setup
python verify_postgres.py  # Test PostgreSQL connection
```

## Code Style Guidelines

### Imports
- Use absolute imports from src package: `from src.agent import axiom_agent`
- Standard library imports first, then third-party, then local imports
- Use `from typing import Optional, List, Dict, Any` for type hints

### Formatting and Types
- Use Python 3.13+ features
- Use Pydantic for data validation models (see src/models.py)
- Use dataclasses for configuration (see src/config.py)
- Use type hints consistently: `def func(param: str) -> Optional[str]:`
- Use async/await for I/O operations

### Naming Conventions
- Classes: PascalCase (e.g., `AgentState`, `DatabaseManager`)
- Functions and variables: snake_case (e.g., `run_stream`, `session_id`)
- Constants: UPPER_CASE (e.g., `DEFAULT_MODEL`, `TIMEOUT`)
- Private methods: prefix with underscore (e.g., `_authenticate`, `_load_memory`)

### Error Handling
- Use try/finally blocks for database session management
- Use specific exceptions rather than bare `except:`
- Log errors with context using structured logging
- Provide fallback behavior for optional dependencies (PostgreSQL/Redis)

### Database Patterns
- Use SQLAlchemy ORM with declarative base
- Always close database sessions in finally blocks
- Use context managers for database operations
- Separate models (src/database.py) from business logic

### Agent Architecture
- Use LangGraph for workflow orchestration
- Implement both streaming and non-streaming responses
- Store session state in Redis, long-term memory in PostgreSQL
- Use Pydantic models for request/response validation

### Configuration Management
- Use environment variables via python-dotenv
- Group related config in dataclasses (DatabaseConfig, RedisConfig, etc.)
- Provide sensible defaults for all settings
- Keep secrets out of code (use .env file)

### Testing Patterns
- Write integration tests for external services
- Test both success and failure scenarios
- Use descriptive function names: `test_database_connection()`
- Print results with clear ✅/❌ indicators for visibility

### File Organization
- src/ package for core functionality
- Root level for applications (fastapi_app.py, chainlit_app.py)
- test_*.py prefix for test files
- Keep models in src/models.py, database in src/database.py

### Security Considerations
- Validate all inputs with Pydantic validators
- Use parameterized queries (SQLAlchemy handles this)
- Never log sensitive information (API keys, passwords)
- Implement proper session management and timeouts

### Performance Notes
- Use async generators for streaming responses (AsyncGenerator)
- Implement Redis caching for session data
- Use connection pooling for database operations
- Set reasonable timeouts for external API calls

## Common Patterns

### Adding New API Endpoints
1. Add Pydantic models to src/models.py
2. Implement endpoints in fastapi_app.py
3. Add error handling and validation
4. Update documentation in README.md

### Extending Agent Workflow
1. Add new node to LangGraph workflow in src/agent.py
2. Implement node function returning updated state
3. Add edge connections in _build_graph method
4. Test with both streaming and non-streaming modes

### Database Schema Changes
1. Update SQLAlchemy models in src/database.py
2. Add migration logic if needed
3. Update corresponding Pydantic models
4. Test with verify_postgres.py