from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from .config import config

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    session_id = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize database engine with proper error handling"""
        try:
            connection_string = config.database.get_connection_string()
            self.engine = create_engine(
                connection_string,
                connect_args={"connect_timeout": 2},  # 2 second timeout
            )
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )
            print("✅ Database engine initialized successfully")
        except Exception as e:
            print(f"⚠️ Database initialization failed: {e}")
            self.engine = None
            self.SessionLocal = None

    def create_tables(self):
        """Create database tables with error handling"""
        if not self.engine:
            print("⚠️ Cannot create tables: database not available")
            return False

        try:
            Base.metadata.create_all(bind=self.engine)
            print("✅ Database tables created/verified")
            return True
        except Exception as e:
            print(f"⚠️ Database table creation failed: {e}")
            return False

    def get_session(self):
        """Get database session with connection retry"""
        if not self.SessionLocal:
            if not self.engine:
                # Try to initialize again
                self._initialize_engine()

            if not self.SessionLocal:
                # Database still not available
                print("⚠️ Database not available for session creation")
                raise Exception("Database not available")

        try:
            return self.SessionLocal()
        except Exception as e:
            print(f"⚠️ Failed to create database session: {e}")
            raise Exception("Database session creation failed")

    def close_session(self, session):
        """Close database session safely"""
        try:
            if session:
                session.close()
        except Exception as e:
            print(f"⚠️ Error closing database session: {e}")

    def is_healthy(self) -> bool:
        """Check if database is healthy"""
        if not self.engine:
            return False

        try:
            with self.engine.connect() as conn:
                from sqlalchemy import text

                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


db_manager = DatabaseManager()
