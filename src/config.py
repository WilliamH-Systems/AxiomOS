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
            print(f"✅ Using DATABASE_URL: {self.database_url[:30]}...")
            return self.database_url

        # Render fallback: try Render-provided individual variables
        render_host = os.getenv("DB_HOST")
        render_user = os.getenv("DB_USER")
        render_password = os.getenv("DB_PASSWORD")
        render_name = os.getenv("DB_NAME")

        if render_host and render_user and render_name:
            print(f"✅ Using Render individual DB variables")
            password_encoded = (
                urllib.parse.quote_plus(render_password) if render_password else ""
            )
            return (
                f"postgresql://{render_user}:{password_encoded}@"
                f"{render_host}:5432/{render_name}"
            )

        # Local development fallback
        print(f"⚠️ Using localhost database (development mode)")
        password_encoded = (
            urllib.parse.quote_plus(self.password) if self.password else ""
        )
        return (
            f"postgresql://{self.username}:{password_encoded}@"
            f"{self.host}:{self.port}/{self.database}"
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

    # Support for Render Key-Value Store
    kv_url: Optional[str] = os.getenv("KV_URL")

    # Fallback to individual components for local development
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")

    def get_connection_kwargs(self) -> dict:
        """Get Redis connection kwargs, prioritizing REDIS_URL or KV_URL"""
        # Try REDIS_URL first (Redis service)
        if self.redis_url:
            print(f"✅ Using REDIS_URL: {self.redis_url[:30]}...")
            return {"use_url": True, "url": self.redis_url}

        # Try KV_URL (Render Key-Value store)
        if self.kv_url:
            print(f"✅ Using KV_URL (Render Key-Value): {self.kv_url[:30]}...")
            return {"use_url": True, "url": self.kv_url}

        # Render fallback: try Render-provided individual variables
        render_host = os.getenv("REDIS_HOST")
        render_password = os.getenv("REDIS_PASSWORD")

        if render_host:
            print(f"✅ Using Render individual Redis variables")
            return {
                "host": render_host,
                "port": 6379,
                "db": 0,
                "password": render_password,
                "decode_responses": True,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "health_check_interval": 30,
            }

        # Local development fallback
        print(f"⚠️ Using localhost Redis (development mode)")
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

        # Local development fallback
        print(f"⚠️ Using localhost Redis (development mode)")
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
