from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import json
import uvicorn
from datetime import datetime
import os

from src.agent import axiom_agent
from src.models import AgentRequestModel, AgentResponseModel, StreamChunkModel
from src.database import db_manager
from src.redis_manager import redis_manager
from src.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and Redis connections"""
    try:
        # Create database tables
        db_manager.create_tables()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")

    try:
        # Test Redis connection
        if redis_manager.ping():
            print("✅ Redis connection successful")
        else:
            print("⚠️ Redis connection failed - using memory fallback")
    except Exception as e:
        print(f"⚠️ Redis initialization failed: {e}")

    print("🚀 AxiomOS API is ready!")
    yield
    print("🛑 AxiomOS API shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="AxiomOS API",
    description="Personal Assistant with Long-term Memory",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware - Configure for production
import os

cors_origins = (
    os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Serve the web interface"""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {
            "message": "AxiomOS API is running",
            "version": "1.0.0",
            "status": "healthy",
            "note": "Web interface not found. Static files may not be built yet.",
        }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    health_status = {
        "status": "healthy",
        "database": False,
        "redis": False,
        "groq_api": bool(config.groq.api_key),
        "database_config": config.database.is_using_url(),
        "redis_config": config.redis.is_using_url() or bool(config.redis.kv_url),
    }

    # Check database
    try:
        db_manager.create_tables()
        health_status["database"] = db_manager.is_healthy()
    except Exception as e:
        print(f"Health check database error: {e}")
        health_status["database"] = False

    # Check Redis
    try:
        health_status["redis"] = redis_manager.ping()
    except Exception as e:
        print(f"Health check Redis error: {e}")
        health_status["redis"] = False

    # Determine overall status
    services_healthy = [
        health_status["database"],
        health_status["redis"],
        health_status["groq_api"],
    ]

    if all(services_healthy):
        health_status["overall"] = "healthy"
    elif health_status["groq_api"] and (
        health_status["database"] or health_status["redis"]
    ):
        health_status["overall"] = "degraded"
    else:
        health_status["overall"] = "unhealthy"

    return health_status


@app.post("/chat", response_model=AgentResponseModel)
async def chat(request: AgentRequestModel):
    """Regular chat endpoint without streaming"""
    try:
        response = axiom_agent.run(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: AgentRequestModel):
    """Streaming chat endpoint"""

    async def generate():
        try:
            async for chunk in axiom_agent.run_stream(request):
                yield f"data: {chunk.json()}\n\n"
        except Exception as e:
            error_chunk = StreamChunkModel(
                token=f"Error: {str(e)}",
                session_id=request.session_id or "unknown",
                is_complete=True,
                final_response=f"Error: {str(e)}",
            )
            yield f"data: {error_chunk.json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session information"""
    try:
        session_data = redis_manager.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"session_id": session_id, "data": session_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    try:
        redis_manager.delete_session(session_id)
        return {"message": "Session deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )


@app.get("/memory/{user_id}")
async def get_user_memory(user_id: int):
    """Get user's long-term memory"""
    try:
        from src.database import LongTermMemory

        db_session = db_manager.get_session()
        try:
            memories = (
                db_session.query(LongTermMemory)
                .filter(LongTermMemory.user_id == user_id)
                .all()
            )

            memory_data = {
                "user_id": user_id,
                "memories": [
                    {
                        "key": memory.key,
                        "value": memory.value,
                        "created_at": memory.created_at.isoformat(),
                        "updated_at": memory.updated_at.isoformat(),
                    }
                    for memory in memories
                ],
            }
            return memory_data
        finally:
            db_session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory: {str(e)}")


@app.post("/memory/{user_id}")
async def save_memory(user_id: int, key: str, value: str):
    """Save a memory for a user"""
    try:
        from src.database import LongTermMemory

        db_session = db_manager.get_session()
        try:
            # Check if memory already exists
            existing_memory = (
                db_session.query(LongTermMemory)
                .filter(LongTermMemory.user_id == user_id, LongTermMemory.key == key)
                .first()
            )

            if existing_memory:
                existing_memory.value = value
                existing_memory.updated_at = datetime.utcnow()
            else:
                new_memory = LongTermMemory(user_id=user_id, key=key, value=value)
                db_session.add(new_memory)

            db_session.commit()
            return {"message": "Memory saved successfully"}
        finally:
            db_session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save memory: {str(e)}")


@app.get("/config")
async def get_config():
    """Get current configuration (without sensitive data)"""
    return {
        "groq_model": config.groq.model,
        "max_tokens": config.groq.max_tokens,
        "temperature": config.groq.temperature,
        "session_timeout": config.session_timeout,
        "log_level": config.log_level,
    }


@app.get("/debug-env")
async def debug_env():
    """Debug environment variables for troubleshooting"""
    import os

    return {
        "database_url_provided": bool(os.getenv("DATABASE_URL")),
        "database_url_prefix": os.getenv("DATABASE_URL", "")[:20] + "..."
        if os.getenv("DATABASE_URL")
        else None,
        "redis_url_provided": bool(os.getenv("REDIS_URL")),
        "redis_url_prefix": os.getenv("REDIS_URL", "")[:20] + "..."
        if os.getenv("REDIS_URL")
        else None,
        "kv_url_provided": bool(os.getenv("KV_URL")),
        "kv_url_prefix": os.getenv("KV_URL", "")[:20] + "..."
        if os.getenv("KV_URL")
        else None,
        "db_host": os.getenv("DB_HOST"),
        "db_port": os.getenv("DB_PORT"),
        "redis_host": os.getenv("REDIS_HOST"),
        "redis_port": os.getenv("REDIS_PORT"),
        "config_database_url": bool(config.database.database_url),
        "config_redis_url": bool(config.redis.redis_url),
        "config_kv_url": bool(config.redis.kv_url),
    }


if __name__ == "__main__":
    # Use Render's port if available, otherwise default to 8000
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level=config.log_level.lower(),
    )
