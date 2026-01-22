# database/session_manager.py
from .db_config import SessionLocal
from contextlib import contextmanager

@contextmanager
def get_session():
    """This function provides a session for other modules to use."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
