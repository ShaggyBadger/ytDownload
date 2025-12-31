import requests
from pathlib import Path
import db
from sqlalchemy import or_
import logging

# Setup module-level logger
logger = logging.getLogger(__name__)

# Constants
FASTAPI_URL = "http://192.168.68.66:5000/new-job"
PRIORITY_LEVEL = 'low'

class DeployJobs:
    """
    This class handles deploying video processing jobs to a FastAPI server.
    """
    def __init__(self):
        self.fastapi_url = FASTAPI_URL
        self.priority_level = PRIORITY_LEVEL
        
        videos_to_deploy = self.find_videos_to_deploy()

        if not videos_to_deploy:
            logger.info("No new videos to deploy for transcription.")
        else:
            logger.info(f"Found {len(videos_to_deploy)} videos to deploy.")
            # input("Press Enter to continue...") # Optional: uncomment for manual confirmation
            for video in videos_to_deploy:
                self.deploy_job(video)
        
        logger.info('Deployment process complete.')

    def find_videos_to_deploy(self):
        """Finds videos that are ready for transcription deployment."""
        logger.info("Finding videos to deploy...")
        session = db.SessionLocal()
        try:
            videos = session.query(db.Video).filter(
                db.Video.stage_2_status == 'completed',
                or_(
                    db.Video.stage_3_status == 'pending',
                    db.Video.stage_3_status == 'failed_deployment'
                )
            ).order_by(db.Video.id.asc()).all()
            return videos
        finally:
            session.close()

    def deploy_job(self, video):
        """Deploys a single video processing job."""
        logger.info(f'Deploying processing job for video: {video.title}...')

        if not video.mp3_path:
            logger.warning(f"No MP3 path found for video: {video.title}. Skipping deployment.")
            self.update_video_status_on_failure(video, 'failed_deployment', "MP3 path not found")
            return

        file_path = Path(video.mp3_path)
        if not file_path.exists():
            logger.error(f"File not found at {file_path} for video: {video.title}. Skipping deployment.")
            self.update_video_status_on_failure(video, 'failed_deployment', "MP3 file not found")
            return

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'audio/mpeg')}
                data = {'priority_level': self.priority_level, 'filename': file_path.name}

                response = requests.post(self.fastapi_url, files=files, data=data)
                response.raise_for_status()
                
                logger.info(f"Successfully deployed {file_path.name}.")
                
                response_data = response.json()
                job_ulid = response_data.get("job_ulid")
                job_status_from_server = response_data.get("status")

                session = db.SessionLocal()
                try:
                    video = session.merge(video)
                    video.stage_3_status = 'deployed'

                    new_job_deployment = db.JobDeployment(
                        video_id=video.id,
                        ulid=job_ulid,
                        job_status=job_status_from_server
                    )
                    session.add(new_job_deployment)
                    session.commit()
                    logger.info(f"JobDeployment for video {video.title} (ULID: {job_ulid}) created with status '{job_status_from_server}'.")
                except Exception as e:
                    session.rollback()
                    logger.error(f"DB Error for {video.title} post-deployment: {e}", exc_info=True)
                finally:
                    session.close()

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error deploying {file_path.name}: {e}", exc_info=True)
            self.update_video_status_on_failure(video, 'failed_deployment', "Network error during deployment")
        except IOError as e:
            logger.error(f"File error for {file_path.name}: {e}", exc_info=True)
            self.update_video_status_on_failure(video, 'failed_deployment', "File I/O error")
        except Exception as e:
            logger.critical(f"Unexpected error deploying {file_path.name}: {e}", exc_info=True)
            self.update_video_status_on_failure(video, 'failed_deployment', "An unexpected error occurred")

    def update_video_status_on_failure(self, video, status, reason):
        """Updates the video status in the DB upon a deployment failure."""
        session = db.SessionLocal()
        try:
            video = session.merge(video)
            video.stage_3_status = status
            # Optional: Add a reason to the video table if you have a column for it
            # video.deployment_error_message = reason 
            session.commit()
            logger.info(f"Updated video {video.title} status to '{status}'.")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update video status for {video.title} after error: {e}", exc_info=True)
        finally:
            session.close()

def prepare_and_transfer_files():
    """
    Initializes the deployment process for videos ready for transcription.
    """
    DeployJobs()

if __name__ == "__main__":
    prepare_and_transfer_files()


# def transfer_all_mp3_info_json():
#     """
#     Prepares and transfers a JSON file containing mp3Id and mp3Name for all
#     videos that have completed stage 2 (MP3 download and trim).
#     """
#     db_session = db.SessionLocal()
#     local_json_path = None
#     try:
#         # 1. Get all videos that have completed stage 2
#         all_completed_mp3_videos = db_session.query(db.Video).filter(
#             db.Video.stage_2_status == "completed"
#         ).all()

#         if not all_completed_mp3_videos:
#             print("No videos with completed MP3s found in the database.")
#             return

#         print(f"Found {len(all_completed_mp3_videos)} videos with completed MP3s.")

#         # 2. Prepare the JSON data with mp3Id and mp3Name
#         json_data = []
#         for video in all_completed_mp3_videos:
#             json_data.append({
#                 "mp3Id": video.id,
#                 "mp3Name": Path(video.mp3_path).name
#             })

#         # Create a temporary local JSON file
#         local_json_path = Path(__file__).parent / "all_files.json"
#         with open(local_json_path, "w") as f:
#             json.dump(json_data, f, indent=2)

#         # 3. Transfer the JSON file
#         print("Transferring all MP3 info JSON to the remote desktop...")
#         # Use the same remote path as the standard transfer
#         sftp_put(str(local_json_path), REMOTE_JSON_PATH)
#         print(f"Transferred {local_json_path.name} to {REMOTE_JSON_PATH}")

#         print("All MP3 info JSON transfer complete.")

#     finally:
#         db_session.close()
#         # Clean up the temporary JSON file
#         if local_json_path and local_json_path.exists():
#             local_json_path.unlink()
