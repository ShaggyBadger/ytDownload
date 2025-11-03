from db import SessionLocal, Video
from sqlalchemy import func

def get_status_char(status):
    """Returns a single character representation of a status."""
    if not status:
        return ' '
    return status[0].upper()

def display_db_info():
    """
    Connects to the database and displays a summary of video statuses.
    """
    db = SessionLocal()
    try:
        total_videos = db.query(Video).count()
        if total_videos == 0:
            print("\nThe database is currently empty.")
            return

        print(f"\n--- Database Status Summary ---")
        print(f"Total videos in database: {total_videos}")

        # Count videos at different stages
        stage1_complete = db.query(Video).filter(Video.stage_1_status == 'completed').count()
        stage2_pending = db.query(Video).filter(Video.stage_2_status == 'pending').count()
        stage2_complete = db.query(Video).filter(Video.stage_2_status == 'completed').count()
        stage2_failed = db.query(Video).filter(Video.stage_2_status == 'failed').count()
        stage3_pending = db.query(Video).filter(Video.stage_3_status == 'pending').count()
        stage3_processing = db.query(Video).filter(Video.stage_3_status == 'processing').count()
        stage3_complete = db.query(Video).filter(Video.stage_3_status == 'complete').count()
        stage3_failed = db.query(Video).filter(Video.stage_3_status == 'failed').count()
        stage4_pending = db.query(Video).filter(Video.stage_4_status == 'pending').count()
        stage4_complete = db.query(Video).filter(Video.stage_4_status == 'complete').count()
        stage4_failed = db.query(Video).filter(Video.stage_4_status == 'failed').count()
        stage5_pending = db.query(Video).filter(Video.stage_5_status == 'pending').count()
        stage5_complete = db.query(Video).filter(Video.stage_5_status == 'complete').count()
        stage5_failed = db.query(Video).filter(Video.stage_5_status == 'failed').count()
        stage6_pending = db.query(Video).filter(Video.stage_6_status == 'pending').count()
        stage6_complete = db.query(Video).filter(Video.stage_6_status == 'complete').count()
        stage6_failed = db.query(Video).filter(Video.stage_6_status == 'failed').count()

        print(f"\n- Stage 1 (Metadata): {stage1_complete} completed")
        print(f"- Stage 2 (MP3 Download):")
        print(f"  - {stage2_pending} pending")
        print(f"  - {stage2_complete} completed")
        print(f"  - {stage2_failed} failed")
        print(f"- Stage 3 (Transcription):")
        print(f"  - {stage3_pending} pending")
        print(f"  - {stage3_processing} processing")
        print(f"  - {stage3_complete} completed")
        print(f"  - {stage3_failed} failed")
        print(f"- Stage 4 (Transcript complete):")
        print(f"  - {stage4_pending} pending")
        print(f"  - {stage4_complete} completed")
        print(f"  - {stage4_failed} failed")
        print(f"- Stage 5 (Python text scrubbing):")
        print(f"  - {stage5_pending} pending")
        print(f"  - {stage5_complete} completed")
        print(f"  - {stage5_failed} failed")
        print(f"- Stage 6 (LLM editing):")
        print(f"  - {stage6_pending} pending")
        print(f"  - {stage6_complete} completed")
        print(f"  - {stage6_failed} failed")
        
        print("\n--- Detailed Video Status ---")
        all_videos = db.query(Video).order_by(Video.id).all()
        for video in all_videos:
            s1 = get_status_char(video.stage_1_status)
            s2 = get_status_char(video.stage_2_status)
            s3 = get_status_char(video.stage_3_status)
            s4 = get_status_char(video.stage_4_status)
            s5 = get_status_char(video.stage_5_status)
            s6 = get_status_char(video.stage_6_status)
            status_line = f"  ID: {video.id:<3} [{s1}|{s2}|{s3}|{s4}|{s5}|{s6}]"
            print(status_line)
            if video.stage_2_status == 'failed' and video.error_message:
                # Indent the error message to align it under the video
                print(f"    └─ Error: {video.error_message}")
        print("-----------------------------")

    finally:
        db.close()

if __name__ == '__main__':
    display_db_info()
