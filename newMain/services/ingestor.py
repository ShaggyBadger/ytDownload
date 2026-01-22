"""
This module provides services for ingesting video information into the database.
It defines functions to add new video entries and manage database sessions.
"""

from database.session_manager import get_session
from database.models import VideoInfo