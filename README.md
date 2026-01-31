# AxiomOS - Personal Assistant with Long-term Memory

AxiomOS is a Python-based personal assistant powered by LangGraph, using Groq API for intelligent responses, with both session and long-term memory capabilities.

The agent is fully functional with:
- Groq API integration working
- Token streaming implemented
- FastAPI backend running
- Chainlit UI available
- Pydantic validation active
- PostgreSQL
- Redis

## Features

- 🤖 **Intelligent Conversations**: Powered by Groq's fast LLM models
- 🧠 **Long-term Memory**: Stores and retrieves important information
- 💾 **Session Memory**: Maintains conversation context
- ⚡ **Token Streaming**: Real-time response streaming + Groq fast LLM speeds
- 🌐 **FastAPI Backend**: RESTful API endpoints
- 💬 **Chainlit UI**: Beautiful chat interface
- 🗄️ **PostgreSQL**: Persistent data storage
- 🔄 **Redis Pub-Sub**: Session management and caching
- ✅ **Pydantic Validation**: Runtime type checking

## Quick Start

### Prerequisites
- Python 3.13+
- PostgreSQL
- Redis

Ensure that PostgreSQL and Redis are both activated/enabled.

### Installation

1. **Clone and setup**
```bash
git clone https://github.com/WilliamH-Systems/AxiomOS
cd AxiomOS
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**
```bash
uv add fastapi chainlit groq python-dotenv uvicorn
```

3. **Configure environment**
```bash
# Your .env file should contain:
GROQ_API_KEY="your_groq_api_key_here"
```

4. **Test integration**
```bash
python test_integration.py
```

### Running the Application

#### Option 1: FastAPI Backend Only
```bash
python fastapi_app.py
```
Then visit http://localhost:8000 for API documentation.

#### Option 2: Chainlit UI Only
```bash
chainlit run chainlit_app.py
```

#### Option 3: Both Services (Recommended)
Open two terminals:
```bash
# Terminal 1
python fastapi_app.py

# Terminal 2  
chainlit run chainlit_app.py
```

## API Endpoints

### Chat
- `POST /chat` - Non-streaming chat
- `POST /chat/stream` - Streaming chat

### Memory Management
- `GET /session/{session_id}` - Get session data
- `DELETE /session/{session_id}` - Delete session
- `GET /memory/{user_id}` - Get user's long-term memory
- `POST /memory/{user_id}` - Save memory

### System
- `GET /` - Health check
- `GET /health` - Detailed health status
- `GET /config` - Current configuration

## Usage Examples

### Using Chainlit UI
1. Start the Chainlit app
2. Open the web interface
3. Start chatting with AxiomOS
4. Use action commands for memory management (managed with regex)

### Using the API
```bash
# Non-streaming chat
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello AxiomOS!", "stream": false}'

# Streaming chat
curl -X POST "http://localhost:8000/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a story", "stream": true}'
```

### Memory Commands
- `remember [information]` - Save to long-term memory
- `recall` - Retrieve from memory
- Regular conversations - Intelligent responses with context

## Configuration

Environment variables:
- `GROQ_API_KEY`: Your Groq API key (required)
- `GROQ_MODEL`: Groq model to use (default: llama-3.1-8b-instant)
- `GROQ_MAX_TOKENS`: Maximum response tokens (default: 1000)
- `GROQ_TEMPERATURE`: Generation temperature (default: 0.7)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL config
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`: Redis config

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Chainlit UI   │    │    FastAPI       │    │   AxiomOS       │
│                 │◄──►│                  │◄──►│   Agent         │
│  Web Interface  │    │   REST API       │    │   (LangGraph)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │                 │
                                     ┌────────▼────────┐ ┌──────▼──────┐
                                     │   PostgreSQL    │ │    Redis    │
                                     │  (Long-term     │ │ (Session    │
                                     │   Memory)       │ │  Memory)    │
                                     └─────────────────┘ └─────────────┘
```

## Development

### Testing
```bash
# Run integration tests
python test_integration.py

# Run with coverage (if installed)
pytest --cov=src tests/
```

## Deployment

### Docker
```dockerfile
[In Progress]
```

### Production Notes
- Use HTTPS in production
- Set proper CORS origins
- Use environment variables for secrets
- Configure database connection pooling
- Set up monitoring and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the BSD 3-Clause License.
