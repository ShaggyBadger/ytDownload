import logging
import requests
from pathlib import Path
import db
from utils import get_video_paths
from sqlalchemy.orm import selectinload

# Setup module-level logger
logger = logging.getLogger(__name__)

# Constants
FASTAPI_URL = "http://192.168.68.66:5000"

class RecoverTranscripts:
    """
    Recovers completed transcripts from the FastAPI server.
    """
    def __init__(self):
        self.fastapi_url = FASTAPI_URL
        ulids_completed = self.query_server_for_completed_jobs()
        
        if ulids_completed:
            logger.info(f"Found {len(ulids_completed)} completed jobs to download.")
            for ulid in ulids_completed:
                self.download_completed_job(ulid)
        else:
            logger.info("No new completed jobs to download.")

    def check_job_status(self, ulid):
        """Checks the status of a single job on the FastAPI server."""
        url = f"{self.fastapi_url}/report-job-status/{ulid}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get('status')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking status for ULID {ulid}: {e}")
            return None

    def query_server_for_completed_jobs(self):
        """
        Queries the local DB for deployed jobs and checks their status on the server.
        Returns a list of ULIDs for jobs that are completed on the server.
        """
        session = db.SessionLocal()
        logger.info("Querying for deployed jobs to check for completion...")
        try:
            # Find jobs that are in-flight
            deployed_jobs = session.query(db.JobDeployment).filter(
                db.JobDeployment.job_status.in_(["pending", "deployed"])
            ).all()

            if not deployed_jobs:
                logger.info("No deployed jobs found to check.")
                return []

            logger.info(f"Found {len(deployed_jobs)} deployed jobs to check.")
            
            completed_ulids = []
            for job in deployed_jobs:
                status = self.check_job_status(job.ulid)
                if status == 'completed':
                    # Update the job status in our local DB to reflect completion
                    job.job_status = 'completed'
                    session.commit()
                    completed_ulids.append(job.ulid)
                    logger.info(f"Job with ULID {job.ulid} is completed on the server.")
            
            return completed_ulids
    
        except Exception as e:
            logger.error(f'Exception occurred while querying for jobs: {e}', exc_info=True)
            session.rollback()
            return []
        finally:
            session.close()

    def download_completed_job(self, ulid):
        """Downloads a transcript, saves it, and updates the database."""
        logger.info(f"Processing download for completed job ULID: {ulid}")
        session = db.SessionLocal()
        try:
            # 1. Find the Job and related Video
            job = session.query(db.JobDeployment).options(
                selectinload(db.JobDeployment.video)
            ).filter(db.JobDeployment.ulid == ulid).first()

            if not job or not job.video:
                logger.error(f"Job with ULID {ulid} or associated video not found in DB.")
                return

            video = job.video
            
            # 2. Determine transcript path using the utility function
            paths = get_video_paths(video)
            local_transcript_path = Path(paths["raw_transcript_path"])
            logger.debug(f"Determined transcript path: {local_transcript_path}")

            # 3. Download the transcript from the server
            download_url = f"{self.fastapi_url}/retrieve-job/{ulid}"
            try:
                response = requests.get(download_url)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download transcript for ULID {ulid}: {e}")
                job.job_status = 'download_failed'
                session.commit()
                return

            # 4. Save the file
            try:
                local_transcript_path.parent.mkdir(parents=True, exist_ok=True)
                local_transcript_path.write_text(response.text, encoding='utf-8')
                logger.info(f"Transcript for {ulid} saved to {local_transcript_path}")
            except IOError as e:
                logger.error(f"Failed to write transcript to disk for ULID {ulid}: {e}")
                job.job_status = 'file_save_failed'
                session.commit()
                return

            # 5. Update the database
            video.transcript_path = str(local_transcript_path)
            video.stage_4_status = 'completed' # Mark transcript as received
            job.job_status = 'retrieved'       # Mark job as retrieved
            
            # Create the entry for the next stage of processing
            self.create_transcript_processing_entry(session, video, local_transcript_path)

            session.commit()
            logger.info(f"Successfully processed and updated database for job {ulid}.")

        except Exception as e:
            logger.error(f'An unexpected error occurred during download process for {ulid}: {e}', exc_info=True)
            session.rollback()
        finally:
            session.close()

    def create_transcript_processing_entry(self, session, video, transcript_path):
        """
        Creates an entry in the TranscriptProcessing table for the new transcript.
        """
        # Check if an entry already exists to avoid duplicates
        existing_tp = session.query(db.TranscriptProcessing).filter(
            db.TranscriptProcessing.video_id == video.id
        ).first()

        if existing_tp:
            logger.warning(f"TranscriptProcessing entry for video {video.id} already exists. Skipping creation.")
            return

        try:
            # Read the transcript to get the word count
            with open(transcript_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            word_count = len(raw_text.split())

            new_tp = db.TranscriptProcessing(
                video_id=video.id,
                raw_transcript_path=str(transcript_path),
                starting_word_count=word_count,
                status="raw_transcript_received"
            )
            session.add(new_tp)
            logger.info(f"Created TranscriptProcessing entry for video {video.id} with word count {word_count}.")
        except Exception as e:
            logger.error(f"Failed to create TranscriptProcessing entry for video {video.id}: {e}", exc_info=True)
            # The session will be rolled back in the calling function's finally block
            raise

def check_remote_status_and_fetch_completed():
    """
    Initializes the recovery process for completed transcripts.
    """
    RecoverTranscripts()

if __name__ == "__main__":
    check_remote_status_and_fetch_completed()
