import os
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Optional

# Load environment variables from .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "axiomos")
    username: str = os.getenv("DB_USER", "axiomos_user")
    password: str = os.getenv("DB_PASSWORD", "")


@dataclass
class RedisConfig:
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")


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
