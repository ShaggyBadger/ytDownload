import json
import re # Needed for title cleanup
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from db import Video, engine, TranscriptProcessing # Import TranscriptProcessing and db


def export_single_sermon(transcript_processing_id):
    """
    Generates a 'sermon_export.txt' file for a specific transcript processing entry.
    Uses the secondary cleaned text and metadata.
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        tp = session.query(TranscriptProcessing).filter(TranscriptProcessing.id == transcript_processing_id).first()
        if not tp:
            print(f"Error: TranscriptProcessing entry with ID {transcript_processing_id} not found.")
            return

        video_dir = Path(tp.raw_transcript_path).parent # Get the video directory (e.g., downloads/1_ytid)
        yt_id = video_dir.name.split('_', 1)[-1] # Extract yt_id from folder name

        # Paths for relevant files
        metadata_path = video_dir / f"{yt_id}_trimmed.meta.txt"
        secondary_transcript_path = video_dir / f"{yt_id}_trimmed.secondary.txt"
        export_path = video_dir / 'sermon_export.txt'

        # Check if files exist
        if not metadata_path.exists():
            print(f"Error: Metadata file not found for transcript {transcript_processing_id} at {metadata_path}")
            return
        if not secondary_transcript_path.exists():
            print(f"Error: Secondary transcript file not found for transcript {transcript_processing_id} at {secondary_transcript_path}")
            return

        # 1. Read and parse metadata (now purely JSON)
        try:
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            title = metadata.get('title')
            thesis = metadata.get('thesis')
            summary = metadata.get('summary')
            if not all([title, thesis, summary]):
                raise ValueError("Missing title, thesis, or summary in metadata.")

        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            print(f"Error processing metadata for transcript {transcript_processing_id}: {e}")
            return

        # 2. Query the database for video record
        sermon_date_str = "Unknown Date"
        try:
            video_record = session.query(Video).filter(Video.id == tp.video_id).first()
            if video_record and video_record.upload_date:
                try:
                    dt_obj = datetime.strptime(video_record.upload_date, '%Y%m%d')
                    sermon_date_str = dt_obj.strftime('%B %d, %Y')
                except (ValueError, TypeError):
                    sermon_date_str = video_record.upload_date
            elif not video_record:
                print(f"Warning: Video with ID '{tp.video_id}' not found in database for transcript {transcript_processing_id}.")
        except Exception as e:
            print(f"Error querying database for video record {tp.video_id}: {e}")
            return
        
        # 3. Read the secondary cleaned transcript
        sermon_text = secondary_transcript_path.read_text(encoding='utf-8')
        
        # 4. Create the sermon_export.txt file
        export_content = (
            f"{title}\n{sermon_date_str}\n\n"
            f"Thesis: {thesis}\n\n"
            f"Summary:\n{summary}\n\n{sermon_text}"
        )
        export_path.write_text(export_content, encoding='utf-8')
        
        print(f"sermon_export.txt created successfully for transcript: {transcript_processing_id} at {export_path}")

    except Exception as e:
        print(f"An unexpected error occurred during export for transcript {transcript_processing_id}: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    export_sermons()
