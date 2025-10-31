import yt_dlp
from pathlib import Path
from pydub import AudioSegment
from db import SessionLocal, Video

def select_videos_to_process():
    """
    Fetches and displays videos pending MP3 processing,
    and prompts the user to select which ones to process.
    """
    db = SessionLocal()
    videos_pending = db.query(Video).filter(
        Video.stage_1_status == "completed",
        Video.stage_2_status != "completed"
    ).all()
    db.close()

    if not videos_pending:
        print("No videos are currently pending for MP3 processing.")
        return []

    print("\n--- Videos Pending MP3 Processing ---")
    for i, video in enumerate(videos_pending, 1):
        print(f"{i}: {video.title}")
    print("all: Process all listed videos")
    print("------------------------------------")

    while True:
        user_input = input("Enter the number of the video to process (or 'all'): ")

        if user_input.lower() == 'all':
            return videos_pending

        try:
            selected_index = int(user_input) - 1
            if 0 <= selected_index < len(videos_pending):
                # Return a list containing the single selected video
                return [videos_pending[selected_index]]
            else:
                print(f"Invalid number. Please enter a number between 1 and {len(videos_pending)}.")
        except ValueError:
            print("Invalid input. Please enter a number or 'all'.")

def process_selected_videos(videos_to_process):
    """
    Downloads and trims MP3 audio for the selected video objects.
    """
    if not videos_to_process:
        print("No videos selected for processing.")
        return

    db = SessionLocal()
    DOWNLOADS_DIR = Path(__file__).parent / "downloads"
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    for video in videos_to_process:
        print(f"\n--- Starting processing for: {video.title} ---")
        video_dir = DOWNLOADS_DIR / video.yt_id
        video_dir.mkdir(exist_ok=True)

        full_audio_path = video_dir / f"{video.yt_id}_full.mp3"
        trimmed_audio_path = video_dir / f"{video.yt_id}_trimmed.mp3"

        try:
            # --- HOOKS for yt-dlp ---
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent_str = d.get('_percent_str', '0.0%').strip()
                    speed_str = d.get('_speed_str', '0.0B/s').strip()
                    eta_str = d.get('_eta_str', '00:00').strip()
                    print(f"\rDownloading: {percent_str} | {speed_str} | ETA: {eta_str}", end='')
                if d['status'] == 'finished':
                    print("\nDownload complete.")

            def postprocessor_hook(d):
                if d['status'] == 'started':
                    print(f"Post-processing: {d['postprocessor']}...")
                if d['status'] == 'finished':
                    print("Post-processing complete.")
            # ------------------------

            # Download
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(full_audio_path).replace('.mp3', ''), # yt-dlp adds the extension
                'keepvideo': False,
                'progress_hooks': [progress_hook],
                'postprocessor_hooks': [postprocessor_hook],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video.webpage_url])

            # Trim
            print("Trimming audio...")
            audio = AudioSegment.from_file(full_audio_path)
            start_ms = video.start_time * 1000
            end_ms = video.end_time * 1000
            trimmed_audio = audio[start_ms:end_ms]
            trimmed_audio.export(trimmed_audio_path, format="mp3")

            # Update DB
            db_video = db.query(Video).filter(Video.id == video.id).first()
            if db_video:
                db_video.stage_2_status = 'completed'
                db_video.download_path = str(full_audio_path)
                db_video.mp3_path = str(trimmed_audio_path)
                db.commit()
                print(f"Successfully processed and saved to {trimmed_audio_path}")

        except Exception as e:
            print(f"\nAn error occurred while processing {video.title}: {e}")
            db.rollback() # Ensure the session is clean before updating status
            db_video = db.query(Video).filter(Video.id == video.id).first()
            if db_video:
                db_video.stage_2_status = 'failed'
                db_video.error_message = str(e)
                db.commit()
    
    db.close()

if __name__ == "__main__":
    selected_videos = select_videos_to_process()
    process_selected_videos(selected_videos)