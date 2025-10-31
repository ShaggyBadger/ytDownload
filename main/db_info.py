from db import SessionLocal, Video
from sqlalchemy import func

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

        print(f"\n- Stage 1 (Metadata): {stage1_complete} completed")
        print(f"- Stage 2 (MP3 Download):")
        print(f"  - {stage2_pending} pending")
        print(f"  - {stage2_complete} completed")
        print(f"  - {stage2_failed} failed")
        
        print("\n--- Detailed Video Status ---")
        all_videos = db.query(Video).order_by(Video.id).all()
        for video in all_videos:
            status_line = (
                f"  ID: {video.id:<3} | "
                f"Title: {video.title[:40]:<40} | "
                f"Stage 1: {video.stage_1_status:<10} | "
                f"Stage 2: {video.stage_2_status:<10}"
            )
            print(status_line)
            if video.stage_2_status == 'failed' and video.error_message:
                # Indent the error message to align it under the video
                print(f"    └─ Error: {video.error_message}")
        print("-----------------------------")

    finally:
        db.close()

if __name__ == '__main__':
    display_db_info()
