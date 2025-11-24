import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime, timezone
from pathlib import Path

# Build the path to the database file within the 'main' directory
db_path = Path(__file__).parent / "videos.db"

Base = declarative_base()
engine = sa.create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    yt_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    uploader = Column(String)
    channel_id = Column(String)
    channel_url = Column(String)
    upload_date = Column(String)
    duration = Column(Integer)
    webpage_url = Column(String)
    description = Column(String)
    thumbnail = Column(String)
    was_live = Column(Boolean)
    live_status = Column(String)

    # === New columns for sermon segment ===
    start_time = Column(Integer, default=0)       # seconds where sermon begins
    end_time = Column(Integer, nullable=True)     # seconds where sermon ends

    # === File paths ===
    download_path = Column(String)
    mp3_path = Column(String)
    transcript_path = Column(String)

    # === Processing state ===
    processing_status = Column(String, default="queued")  # overall state
    stage_1_status = Column(String, default="pending")    # Collect metadata
    stage_2_status = Column(String, default="pending")    # Download & trim MP3
    stage_3_status = Column(String, default="pending")    # Whisper transcription
    stage_4_status = Column(String, default="pending")    # Transcript complete
    stage_5_status = Column(String, default="pending")    # Python text scrubbing
    stage_6_status = Column(String, default="pending")    # LLM editing

    # === Errors and timestamps ===
    error_message = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class TranscriptProcessing(Base):
    __tablename__ = "transcript_processing"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    raw_transcript_path = Column(String)
    initial_cleaning_path = Column(String)
    secondary_cleaning_path = Column(String)
    python_scrub_path = Column(String)
    final_pass_path = Column(String)
    metadata_path = Column(String)
    book_ready_path = Column(String)
    starting_word_count = Column(Integer)
    final_word_count = Column(Integer)
    status = Column(String, default="raw_transcript_received")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
