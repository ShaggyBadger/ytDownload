import logging
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from pathlib import Path

from config import config

logger = logging.getLogger(__name__)


# Helper function to get current UTC time
def utcnow():
    return datetime.now(timezone.utc)


# Build the path to the database file within the 'main' directory
db_path = config.DATABASE_PATH
logger.debug("Database path constructed: %s", db_path)

# SQLAlchemy setup
Base = declarative_base()
engine = sa.create_engine(f"sqlite:///{db_path}")
logger.debug("SQLAlchemy engine created for: %s", engine.url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.debug("SQLAlchemy SessionLocal factory created.")

if __name__ == "__main__":
    # Base.metadata.create_all(bind=engine)
    logger.info(f"Database will be created at: {db_path}")
