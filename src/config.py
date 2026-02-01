import os
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Optional
import urllib.parse

# Load environment variables from .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    # Prioritize DATABASE_URL for production (Render)
    database_url: Optional[str] = os.getenv("DATABASE_URL")

    # Fallback to individual components for local development
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "axiomos")
    username: str = os.getenv("DB_USER", "axiomos_user")
    password: str = os.getenv("DB_PASSWORD", "")

    def get_connection_string(self) -> str:
        """Get database connection string, prioritizing DATABASE_URL"""
        if self.database_url:
            return self.database_url

        # Build connection string from components
        password_encoded = (
            urllib.parse.quote_plus(self.password) if self.password else ""
        )
        return (
            f"postgresql://{self.username}:{password_encoded}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    def is_using_url(self) -> bool:
        """Check if using full DATABASE_URL"""
        return bool(self.database_url)


@dataclass
class RedisConfig:
    # Prioritize REDIS_URL for production (Render)
    redis_url: Optional[str] = os.getenv("REDIS_URL")

    # Fallback to individual components for local development
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")

    def get_connection_kwargs(self) -> dict:
        """Get Redis connection kwargs, prioritizing REDIS_URL"""
        if self.redis_url:
            # For URL-based connection, we'll handle this in redis_manager
            return {"use_url": True, "url": self.redis_url, "decode_responses": True}

        # Build from individual components
        return {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "password": self.password,
            "decode_responses": True,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30,
        }

    def is_using_url(self) -> bool:
        """Check if using full REDIS_URL"""
        return bool(self.redis_url)


@dataclass
class GroqConfig:
    api_key: str = os.getenv("GROQ_API_KEY", "")
    model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    max_tokens: int = int(os.getenv("GROQ_MAX_TOKENS", "1000"))
    temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.7"))


@dataclass
class AxiomOSConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    groq: GroqConfig = field(default_factory=GroqConfig)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour


config = AxiomOSConfig()
