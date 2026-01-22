import sqlalchemy as sa
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker
    )
from datetime import datetime, timezone
from pathlib import Path

from config import config

# Helper function to get current UTC time
def utcnow():
    return datetime.now(timezone.utc)

# Build the path to the database file within the 'main' directory
db_path = config.DATABASE_PATH

# SQLAlchemy setup
Base = declarative_base()
engine = sa.create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if __name__ == "__main__":
    #Base.metadata.create_all(bind=engine)
    print(f"Database will be created at: {db_path}")
