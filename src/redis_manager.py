import redis
import json
from typing import Dict, Any, Optional
from .config import config


class RedisManager:
    def __init__(self):
        self.client = None
        # Don't connect during __init__ to avoid hanging

    def _ensure_connected(self):
        if self.client is None:
            try:
                self.client = redis.Redis(
                    host=config.redis.host,
                    port=config.redis.port,
                    db=config.redis.db,
                    password=config.redis.password,
                    decode_responses=True,
                    socket_connect_timeout=5,  # 5 second timeout
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                # Test connection
                result = self.client.ping()
                print(f"Redis connected successfully: {result}")
            except Exception as e:
                print(f"Redis connection failed: {e}")
                self.client = None
                raise Exception("Redis not available")

    def ping(self) -> bool:
        try:
            self._ensure_connected()
            return self.client.ping()
        except Exception:
            return False

    def set_session_data(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        self._ensure_connected()
        key = f"session:{session_id}"
        self.client.setex(key, ttl, json.dumps(data))

    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_connected()
        key = f"session:{session_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None

    def delete_session(self, session_id: str):
        self._ensure_connected()
        key = f"session:{session_id}"
        self.client.delete(key)

    def publish_message(self, channel: str, message: Dict[str, Any]):
        self.client.publish(channel, json.dumps(message))

    def subscribe_to_channel(self, channel: str):
        pubsub = self.client.pubsub()
        pubsub.subscribe(channel)
        return pubsub


redis_manager = RedisManager()
