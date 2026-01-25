"""
This module holds the models for the database using SQLAlchemy ORM.
It defines tables for video information, job tracking, and processing stages.

It also has the StageState enum to lock in the possible states for each processing stage,
and it defines the order of processing stages in STAGE_ORDER.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Enum,
    Text,
    )
from sqlalchemy.orm import relationship
from pathlib import Path
import enum
import ulid

from config import config
from .db_config import Base, utcnow

# constant variable to maintain the stage order
STAGE_ORDER = [
    "download_video",
    "extract_audio",
    "transcribe_whisper",
    "format_gemini",
    "extract_metadata",
    "edit_local_llm",
    "build_chapter",
]

# lock in the available states for processing stages
class StageState(enum.Enum):
    pending = "pending"
    running = "running"
    blocked = "blocked"
    success = "success"
    failed = "failed"


class VideoInfo(Base):
    __tablename__ = "video_info"

    # === make primary key ===
    id = Column(Integer, primary_key=True, index=True)

    # === data from youtube-dl / yt-dlp ===
    yt_id = Column(String, unique=False, nullable=False)
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

    # === Timestamps ===
    created_at = Column(DateTime(timezone=True), default=utcnow)


class JobInfo(Base):
    __tablename__ = "job_info"

    id = Column(Integer, primary_key=True, index=True)
    job_ulid = Column(String, unique=True, default=lambda: str(ulid.ulid()))

    # info on which video and what segment we want for this job
    video_id = Column(Integer, ForeignKey("video_info.id"), nullable=False)
    audio_start_time = Column(Integer, default=0)  # in seconds
    audio_end_time = Column(Integer, default=0)    # in seconds

    # storage directory
    job_directory = Column(String)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    stages = relationship("JobStage", back_populates="job")


class JobStage(Base):
    __tablename__ = "job_stage"

    # Define a unique constraint to ensure each job has unique stage names
    __table_args__ = (
        UniqueConstraint("job_id", "stage_name"),
    )

    # Primary key and foreign key to JobInfo
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("job_info.id"), nullable=False)

    # Stage details
    stage_name = Column(String(64), nullable=False)
    state = Column(
        Enum(StageState),
        nullable=False,
        default=StageState.pending,
    )

    # Tracking attempts and errors
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text)

    started_at = Column(DateTime)
    finished_at = Column(DateTime)

    next_eligible_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
    )

    output_path = Column(Text) # Path to the output file for this stage

    job = relationship("JobInfo", back_populates="stages")