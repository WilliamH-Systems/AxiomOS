import redis
import json
from typing import Dict, Any, Optional
from .config import config


class RedisManager:
    def __init__(self):
        self.client = None
        self.fallback_mode = False
        self.memory_storage = {}  # In-memory fallback storage
        # Don't connect during __init__ to avoid hanging

    def _ensure_connected(self):
        """Ensure Redis is connected, with graceful fallback to memory"""
        if self.client is None and not self.fallback_mode:
            try:
                kwargs = config.redis.get_connection_kwargs()
                if kwargs.get("use_url"):
                    # Use Redis URL
                    self.client = redis.from_url(kwargs["url"])
                else:
                    # Use individual connection parameters
                    kwargs.pop("use_url", None)
                    kwargs.pop("url", None)
                    self.client = redis.Redis(**kwargs)

                # Test connection
                result = self.client.ping()
                print(f"✅ Redis connected successfully: {result}")
            except Exception as e:
                print(f"⚠️ Redis connection failed: {e}")
                print("🔄 Using in-memory fallback for session storage")
                self.client = None
                self.fallback_mode = True
                # Don't raise exception - use fallback mode instead

    def ping(self) -> bool:
        try:
            if self.fallback_mode:
                return False  # Fallback mode is always "unhealthy" but functional
            self._ensure_connected()
            if self.client:
                # Use sync ping - we're using sync Redis
                return bool(self.client.ping())
            return False
        except Exception:
            return False

    def set_session_data(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        """Set session data with Redis or memory fallback"""
        if self.fallback_mode:
            # Memory fallback (ignores TTL for simplicity)
            self.memory_storage[f"session:{session_id}"] = data
            return

        self._ensure_connected()
        if self.client:
            key = f"session:{session_id}"
            self.client.setex(key, ttl, json.dumps(data))

    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data with Redis or memory fallback"""
        if self.fallback_mode:
            return self.memory_storage.get(f"session:{session_id}")

        self._ensure_connected()
        if self.client:
            key = f"session:{session_id}"
            data = self.client.get(key)
            if data and isinstance(data, (str, bytes)):
                return json.loads(data)
        return None

    def delete_session(self, session_id: str):
        """Delete session with Redis or memory fallback"""
        if self.fallback_mode:
            self.memory_storage.pop(f"session:{session_id}", None)
            return

        self._ensure_connected()
        if self.client:
            key = f"session:{session_id}"
            self.client.delete(key)

    def publish_message(self, channel: str, message: Dict[str, Any]):
        """Publish message (Redis only - not supported in fallback mode)"""
        if self.fallback_mode:
            print(f"⚠️ Redis pub/sub not available in fallback mode")
            return

        self._ensure_connected()
        if self.client:
            self.client.publish(channel, json.dumps(message))

    def subscribe_to_channel(self, channel: str):
        """Subscribe to channel (Redis only - not supported in fallback mode)"""
        if self.fallback_mode:
            print(f"⚠️ Redis pub/sub not available in fallback mode")
            return None

        self._ensure_connected()
        if self.client:
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            return pubsub


redis_manager = RedisManager()
