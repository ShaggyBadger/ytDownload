import logging
from .db_config import SessionLocal
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def get_session():
    """This function provides a session for other modules to use."""
    session = SessionLocal()
    logger.debug("Opening new SQLAlchemy session.")
    try:
        yield session
        session.commit()
        logger.debug("Session committed successfully.")
    except Exception:
        session.rollback()
        logger.error("Session rolled back due to exception.", exc_info=True)
        raise
    finally:
        session.close()
        logger.debug("SQLAlchemy session closed.")