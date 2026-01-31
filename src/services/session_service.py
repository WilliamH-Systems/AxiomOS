import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from .agent_state import AgentState
from ..database import db_manager, Session as DBSession
from ..config import config

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def authenticate_or_create_session(self, state: AgentState) -> AgentState:
        if not state.session_id:
            new_session_id = str(uuid.uuid4())
            self.logger.info(f"Creating new session: {new_session_id}")
            state = state.with_session_id(new_session_id)

        try:
            session_db = db_manager.get_session()
            try:
                session = (
                    session_db.query(DBSession)
                    .filter(
                        DBSession.session_id == state.session_id,
                        DBSession.expires_at > datetime.now(timezone.utc),
                    )
                    .first()
                )

                if session:
                    self.logger.debug(f"Found existing session: {state.session_id}")
                    state = state.with_user_id(session.user_id)
                else:
                    self.logger.debug(
                        f"Creating new database session: {state.session_id}"
                    )
                    new_session = DBSession(
                        user_id=1,  # Default user for now
                        session_id=state.session_id,
                    )
                    new_session.expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=config.session_timeout
                    )
                    session_db.add(new_session)
                    session_db.commit()
                    state = state.with_user_id(new_session.user_id)

            finally:
                session_db.close()
        except Exception as e:
            self.logger.warning(f"Database not available, using fallback: {e}")
            state = state.with_user_id(1)  # Fallback: use default user

        return state

    async def extend_session(self, session_id: str) -> bool:
        try:
            session_db = db_manager.get_session()
            try:
                session = (
                    session_db.query(DBSession)
                    .filter(DBSession.session_id == session_id)
                    .first()
                )

                if session:
                    session_db.query(DBSession).filter(
                        DBSession.session_id == session_id
                    ).update(
                        {
                            DBSession.expires_at: datetime.now(timezone.utc)
                            + timedelta(seconds=config.session_timeout)
                        }
                    )
                    session_db.commit()
                    self.logger.debug(f"Extended session: {session_id}")
                    return True
                return False
            finally:
                session_db.close()
        except Exception as e:
            self.logger.error(f"Failed to extend session {session_id}: {e}")
            return False

    async def validate_session(self, session_id: str) -> Optional[int]:
        try:
            session_db = db_manager.get_session()
            try:
                session = (
                    session_db.query(DBSession)
                    .filter(
                        DBSession.session_id == session_id,
                        DBSession.expires_at > datetime.now(timezone.utc),
                    )
                    .first()
                )

                return session.user_id if session else None
            finally:
                session_db.close()
        except Exception as e:
            self.logger.error(f"Failed to validate session {session_id}: {e}")
            return None
