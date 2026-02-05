from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional
import asyncio
import json
import uvicorn
from datetime import datetime
import os

from src.agent import axiom_agent
from src.models import AgentRequestModel, AgentResponseModel, StreamChunkModel, SettingsModel, SettingsResponseModel
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


@app.get("/api/health")
async def api_health_check():
    """API health check for frontend"""
    return await health_check()


@app.post("/chat", response_model=AgentResponseModel)
async def chat(request: AgentRequestModel):
    """Regular chat endpoint without streaming"""
    try:
        response = axiom_agent.run(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.post("/api/chat", response_model=AgentResponseModel)
async def api_chat(request: AgentRequestModel):
    """API chat endpoint for frontend with session persistence"""
    try:
        # Ensure session exists
        session_id = request.session_id
        if not session_id:
            # Create new session if none provided
            import uuid
            session_id = str(uuid.uuid4())
            request.session_id = session_id
            
            # Initialize session data
            session_data = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "messages": [],
                "status": "active",
                "title": f"New Chat {session_id[:8]}",
                "message_count": 0
            }
            redis_manager.set_session_data(session_id, session_data)
        
        # Store user message in session
        session_data = redis_manager.get_session_data(session_id) or {}
        messages = session_data.get("messages", [])
        
        user_message = {
            "content": request.message,
            "type": "user",
            "timestamp": datetime.utcnow().isoformat()
        }
        messages.append(user_message)
        
        # Get AI response
        response = axiom_agent.run(request)
        
        # Store AI response in session
        assistant_message = {
            "content": response.response,
            "type": "assistant", 
            "timestamp": datetime.utcnow().isoformat()
        }
        messages.append(assistant_message)
        
        # Update session data
        session_data.update({
            "messages": messages,
            "message_count": len(messages),
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Update session title based on first user message if still default
        if session_data.get("title", "").startswith("New Chat") and len(messages) == 2:
            # Use first 50 chars of first user message as title
            title = request.message[:50] + ("..." if len(request.message) > 50 else "")
            session_data["title"] = title
        
        redis_manager.set_session_data(session_id, session_data)
        
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


@app.post("/api/sessions")
async def create_session():
    """Create a new session"""
    import uuid
    session_id = str(uuid.uuid4())
    
    # Initialize session data with more comprehensive information
    session_data = {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "messages": [],
        "status": "active",
        "title": f"New Chat {session_id[:8]}",  # Default title
        "message_count": 0
    }
    
    # Store session
    redis_manager.set_session_data(session_id, session_data)
    
    return {"session_id": session_id, "status": "created", "title": session_data["title"]}


@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions from Redis or fallback storage"""
    try:
        sessions = []
        
        if redis_manager.fallback_mode:
            # In fallback mode, get sessions from memory storage
            session_keys = [key for key in redis_manager.memory_storage.keys() if key.startswith("session:")]
            
            for key in session_keys:
                session_data = redis_manager.memory_storage[key]
                if session_data:
                    session_id = key.replace("session:", "")
                    sessions.append({
                        "session_id": session_id,
                        "title": session_data.get("title", f"Session {session_id[:8]}"),
                        "created_at": session_data.get("created_at", datetime.utcnow().isoformat()),
                        "message_count": len(session_data.get("messages", [])),
                        "status": session_data.get("status", "active")
                    })
        else:
            # For Redis, scan for session keys
            redis_manager._ensure_connected()
            if redis_manager.client:
                try:
                    # Look for session keys with a pattern (Redis SCAN)
                    for key in redis_manager.client.scan_iter(match="session:*", count=100):
                        try:
                            # Handle both string and bytes keys
                            if isinstance(key, bytes):
                                key_str = key.decode('utf-8')
                            else:
                                key_str = str(key)
                            
                            session_id = key_str.replace("session:", "")
                            session_data = redis_manager.get_session_data(session_id)
                            
                            if session_data:
                                sessions.append({
                                    "session_id": session_id,
                                    "title": session_data.get("title", f"Session {session_id[:8]}"),
                                    "created_at": session_data.get("created_at", datetime.utcnow().isoformat()),
                                    "message_count": len(session_data.get("messages", [])),
                                    "status": session_data.get("status", "active")
                                })
                        except Exception as e:
                            print(f"Error processing session key {key}: {e}")
                            continue
                except Exception as e:
                    print(f"Error scanning Redis sessions: {e}")
        
        # Sort by creation time (newest first)
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"sessions": sessions}
        
    except Exception as e:
        print(f"Error listing sessions: {e}")
        # Return empty sessions list on error
        return {"sessions": []}


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get messages for a session"""
    try:
        session_data = redis_manager.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session_data.get("messages", [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


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


@app.get("/api/memories")
async def api_get_memories(user_id: Optional[int] = 1):
    """Get memories for frontend from actual database"""
    try:
        from src.database import LongTermMemory

        db_session = db_manager.get_session()
        try:
            memories = (
                db_session.query(LongTermMemory)
                .filter(LongTermMemory.user_id == user_id)
                .order_by(LongTermMemory.created_at.desc())
                .all()
            )

            # Transform database records to frontend format
            memory_data = []
            for memory in memories:
                # Extract category from key or use default
                category = "general"
                if ":" in memory.key:
                    category = memory.key.split(":")[0]
                
                memory_data.append({
                    "id": f"mem-{memory.id}",
                    "title": memory.key.replace("_", " ").title(),
                    "content": str(memory.value),
                    "type": "long_term",
                    "category": category,
                    "created_at": memory.created_at.isoformat(),
                    "updated_at": memory.updated_at.isoformat()
                })

            return memory_data
        finally:
            db_session.close()
    except Exception as e:
        print(f"Error retrieving memories: {e}")
        # Return empty list on error to avoid frontend breaking
        return []


@app.get("/api/memories/categories")
async def api_get_memory_categories(user_id: Optional[int] = 1):
    """Get memory categories for frontend from actual database"""
    try:
        from src.database import LongTermMemory
        from collections import Counter

        db_session = db_manager.get_session()
        try:
            memories = (
                db_session.query(LongTermMemory)
                .filter(LongTermMemory.user_id == user_id)
                .all()
            )

            # Extract categories from memory keys
            categories = Counter()
            for memory in memories:
                category = "general"
                if ":" in memory.key:
                    category = memory.key.split(":")[0]
                categories[category] += 1

            # Convert to frontend format
            return [
                {"name": category, "count": count}
                for category, count in categories.most_common()
            ]
        finally:
            db_session.close()
    except Exception as e:
        print(f"Error retrieving memory categories: {e}")
        # Return empty list on error to avoid frontend breaking
        return []


@app.get("/api/memories/export")
async def api_export_memories(user_id: Optional[int] = 1):
    """Export memories from actual database"""
    import json
    from fastapi.responses import Response
    
    memories = await api_get_memories(user_id)
    
    # Create JSON response for download
    json_data = json.dumps(memories, indent=2)
    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=axiomos-memories.json"}
    )


@app.delete("/api/memories/session")
async def api_clear_session_memories():
    """Clear session memories"""
    # Mock implementation
    return {"message": "Session memories cleared successfully"}


@app.delete("/api/memories/{memory_id}")
async def api_delete_memory(memory_id: str, user_id: Optional[int] = 1):
    """Delete a specific memory from database"""
    try:
        from src.database import LongTermMemory

        # Extract numeric ID from memory_id (format: "mem-{id}")
        if not memory_id.startswith("mem-"):
            raise HTTPException(status_code=400, detail="Invalid memory ID format")
        
        try:
            db_memory_id = int(memory_id.split("-")[1])
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid memory ID format")

        db_session = db_manager.get_session()
        try:
            # Find and delete the memory
            memory = (
                db_session.query(LongTermMemory)
                .filter(LongTermMemory.id == db_memory_id, LongTermMemory.user_id == user_id)
                .first()
            )
            
            if not memory:
                raise HTTPException(status_code=404, detail="Memory not found")
            
            db_session.delete(memory)
            db_session.commit()
            
            return {"message": f"Memory {memory_id} deleted successfully"}
        finally:
            db_session.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")


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


@app.delete("/memory/{user_id}")
async def delete_memory(user_id: int, key: Optional[str] = None):
    """Delete memory/memories for a user"""
    try:
        from src.database import LongTermMemory

        db_session = db_manager.get_session()
        try:
            if key:
                # Delete specific memory
                deleted_count = (
                    db_session.query(LongTermMemory)
                    .filter(
                        LongTermMemory.user_id == user_id, LongTermMemory.key == key
                    )
                    .delete()
                )
                if deleted_count > 0:
                    return {"message": f"Successfully deleted memory '{key}'"}
                else:
                    raise HTTPException(
                        status_code=404, detail=f"Memory '{key}' not found"
                    )
            else:
                # Delete all memories for user
                deleted_count = (
                    db_session.query(LongTermMemory)
                    .filter(LongTermMemory.user_id == user_id)
                    .delete()
                )
                return {"message": f"Successfully deleted {deleted_count} memories"}
        finally:
            db_session.commit()
            db_session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete memory: {str(e)}"
        )


@app.get("/api/settings", response_model=SettingsModel)
async def get_settings():
    """Get current AI settings"""
    try:
        return SettingsModel(
            model=config.groq.model,
            temperature=config.groq.temperature,
            max_tokens=config.groq.max_tokens
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


@app.post("/api/settings", response_model=SettingsResponseModel)
async def update_settings(settings: SettingsModel):
    """Update AI settings"""
    try:
        # Update the configuration
        config.groq.update_settings(
            model=settings.model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )
        
        return SettingsResponseModel(
            success=True,
            message="Settings updated successfully",
            settings=settings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


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
