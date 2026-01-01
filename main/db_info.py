from db import SessionLocal, Video, TranscriptProcessing
from sqlalchemy import func
from logger import setup_logger

logger = setup_logger(__name__)

def get_status_char(status):
    """Returns a single character representation of a status."""
    if not status:
        return ' '
    return status[0].upper()

def get_post_processing_chars(tp_status):
    """
    Returns a 4-character string representing the status of
    [Initial Clean|Secondary Clean|Metadata Gen|Sermon Export].
    """
    pp_chars = [' ', ' ', ' ', ' '] # Default to Not Started

    if not tp_status:
        return "".join(pp_chars)

    # Completion states
    if tp_status == "sermon_export_complete":
        pp_chars = ['C', 'C', 'C', 'C']
    elif tp_status == "metadata_generation_complete":
        pp_chars = ['C', 'C', 'C', 'P']
    elif tp_status == "secondary_cleaning_complete":
        pp_chars = ['C', 'C', 'P', ' ']
    elif tp_status == "initial_cleaning_complete":
        pp_chars = ['C', 'P', ' ', ' ']
    elif tp_status == "raw_transcript_received":
        pp_chars = ['P', ' ', ' ', ' ']
    # Failure/Quota states (these override completion if failure occurs at a later stage)
    elif 'quota_exceeded' in tp_status:
        if 'initial_cleaning' in tp_status:
            pp_chars = ['Q', 'Q', 'Q', 'Q']
        elif 'secondary_cleaning' in tp_status:
            pp_chars = ['C', 'Q', 'Q', 'Q']
        elif 'metadata_generation' in tp_status:
            pp_chars = ['C', 'C', 'Q', 'Q']
        elif 'sermon_export' in tp_status:
            pp_chars = ['C', 'C', 'C', 'Q']
        else: # Generic quota exceeded, mark all pending/unknown as Q
            for i in range(4):
                if pp_chars[i] == ' ' or pp_chars[i] == 'P': pp_chars[i] = 'Q'
    elif '_failed' in tp_status:
        if 'initial_cleaning' in tp_status:
            pp_chars = ['F', 'F', 'F', 'F']
        elif 'secondary_cleaning' in tp_status:
            pp_chars = ['C', 'F', 'F', 'F']
        elif 'metadata_generation' in tp_status:
            pp_chars = ['C', 'C', 'F', 'F']
        elif 'sermon_export' in tp_status:
            pp_chars = ['C', 'C', 'C', 'F']
        else: # Generic failed, mark all pending/unknown as F
            for i in range(4):
                if pp_chars[i] == ' ' or pp_chars[i] == 'P': pp_chars[i] = 'F'
    else: # Unknown status
        pp_chars = ['X', ' ', ' ', ' '] # Mark first as Unknown

    return "".join(pp_chars)

def display_db_info():
    """
    Connects to the database and displays a summary of video statuses.
    """
    db = SessionLocal()
    try:
        total_videos = db.query(Video).count()
        if total_videos == 0:
            logger.info("The database is currently empty.")
            return

        logger.info("--- Database Status Summary ---")
        logger.info(f"Total videos in database: {total_videos}")

        # Count videos at different stages
        stage1_complete = db.query(Video).filter(Video.stage_1_status == 'completed').count()
        stage2_pending = db.query(Video).filter(Video.stage_2_status == 'pending').count()
        stage2_complete = db.query(Video).filter(Video.stage_2_status == 'completed').count()
        stage2_failed = db.query(Video).filter(Video.stage_2_status == 'failed').count()
        stage3_pending = db.query(Video).filter(Video.stage_3_status == 'pending').count()
        stage3_processing = db.query(Video).filter(Video.stage_3_status == 'processing').count()
        stage3_complete = db.query(Video).filter(Video.stage_3_status == 'complete').count()
        stage3_failed = db.query(Video).filter(Video.stage_3_status == 'failed').count()
        
        # New post-processing stages based on TranscriptProcessing table
        tp_raw = db.query(TranscriptProcessing).filter(TranscriptProcessing.status == 'raw_transcript_received').count()
        tp_initial_cleaning = db.query(TranscriptProcessing).filter(TranscriptProcessing.status == 'initial_cleaning_complete').count()
        tp_secondary_cleaning = db.query(TranscriptProcessing).filter(TranscriptProcessing.status == 'secondary_cleaning_complete').count()
        tp_metadata_gen = db.query(TranscriptProcessing).filter(TranscriptProcessing.status == 'metadata_generation_complete').count()
        tp_sermon_export = db.query(TranscriptProcessing).filter(TranscriptProcessing.status == 'sermon_export_complete').count()
        tp_quota_exceeded = db.query(TranscriptProcessing).filter(TranscriptProcessing.status.like('%_quota_exceeded')).count()
        tp_failed = db.query(TranscriptProcessing).filter(TranscriptProcessing.status.like('%_failed%')).count() - tp_quota_exceeded
        
        logger.info(f"- Stage 1 (Metadata): {stage1_complete} completed")
        logger.info("- Stage 2 (MP3 Download):")
        logger.info(f"  - {stage2_pending} pending")
        logger.info(f"  - {stage2_complete} completed")
        logger.info(f"  - {stage2_failed} failed")
        logger.info("- Stage 3 (Transcription):")
        logger.info(f"  - {stage3_pending} pending")
        logger.info(f"  - {stage3_processing} processing")
        logger.info(f"  - {stage3_complete} completed")
        logger.info(f"  - {stage3_failed} failed")
        logger.info("--- Post-Processing Stages ---")
        logger.info(f"  - Raw Transcript Received (ready for Initial Cleaning): {tp_raw}")
        logger.info(f"  - Initial Cleaning Complete (ready for Secondary Cleaning): {tp_initial_cleaning}")
        logger.info(f"  - Secondary Cleaning Complete (ready for Metadata Generation): {tp_secondary_cleaning}")
        logger.info(f"  - Metadata Generation Complete (ready for Sermon Export): {tp_metadata_gen}")
        logger.info(f"  - Sermon Export Complete: {tp_sermon_export}")
        if tp_quota_exceeded > 0:
            logger.info(f"  - Quota Exceeded: {tp_quota_exceeded} (processing halted)")
        if tp_failed > 0:
            logger.info(f"  - Failed (non-quota): {tp_failed} (review logs)")
        
        logger.info("--- Detailed Video Status ---")
        # --- Detailed Status Legend ---
        logger.info("Legend: C=Completed, P=Pending, F=Failed, Q=Quota Exceeded, U=Unknown/Not Applicable")
        logger.info("Video Stages: 1=Metadata, 2=MP3 Download, 3=Transcription")
        logger.info("PP Stages: 1=Initial Clean, 2=Secondary Clean, 3=Metadata Gen, 4=Sermon Export")
        logger.info("---")
        # --- Header Row ---
        logger.info(f"{'ID':<4} | {'V1':^2} {'V2':^2} {'V3':^2} | {'PP1':^3} {'PP2':^3} {'PP3':^3} {'PP4':^3} | Errors")
        logger.info("-----|----------|-----------------|---------------------------------")


        all_videos_with_tp = db.query(Video, TranscriptProcessing).outerjoin(
            TranscriptProcessing, Video.id == TranscriptProcessing.video_id
        ).order_by(Video.id).all()

        for video, tp in all_videos_with_tp:
            # Video stages
            v1_char = get_status_char(video.stage_1_status)
            v2_char = get_status_char(video.stage_2_status)
            v3_char = get_status_char(video.stage_3_status)

            # Post-processing stages
            pp_chars_str = get_post_processing_chars(tp.status if tp else None)

            # Error message snippet
            error_snippet = ""
            if video.stage_2_status == 'failed' and video.error_message:
                error_snippet += f"Video Error: {video.error_message[:30]}..."
            if tp and ('_failed' in tp.status or 'quota_exceeded' in tp.status):
                if error_snippet: error_snippet += " | "
                error_snippet += f"PP Status: {tp.status}"
            
            # Print the line
            logger.info(f"{video.id:<4} | {v1_char:^2} {v2_char:^2} {v3_char:^2} | {pp_chars_str[0]:^3} {pp_chars_str[1]:^3} {pp_chars_str[2]:^3} {pp_chars_str[3]:^3} | {error_snippet}")
                
        logger.info("-----------------------------")

    finally:
        db.close()

if __name__ == '__main__':
    display_db_info()
