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
        self.engine = create_engine(
            f"postgresql://{config.database.username}:{config.database.password}@"
            f"{config.database.host}:{config.database.port}/{config.database.database}",
            connect_args={"connect_timeout": 2},  # 2 second timeout
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self):
        if self.engine:
            Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        # Try to connect on first use
        if self.SessionLocal is None:
            try:
                self.engine = create_engine(
                    f"postgresql://{config.database.username}:{config.database.password}@"
                    f"{config.database.host}:{config.database.port}/{config.database.database}",
                    connect_args={"connect_timeout": 2},  # 2 second timeout
                )
                self.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )
            except Exception as e:
                print(f"Database connection failed: {e}")
                raise Exception("Database not available")

        return self.SessionLocal()

    def close_session(self, session):
        if session:
            session.close()


db_manager = DatabaseManager()
