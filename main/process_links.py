import yt_dlp
import csv
from pathlib import Path
from db import SessionLocal, Video


def get_video_metadata(url):
    """
    Fetches video metadata using yt-dlp without downloading the video.

    Args:
        url (str): The URL of the YouTube video.

    Returns:
        dict: A dictionary containing the video's metadata.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            
            # Create a new dictionary with only the required keys
            video_details = {
                'yt_id': info_dict.get('id'),
                'title': info_dict.get('title'),
                'uploader': info_dict.get('uploader'),
                'channel_id': info_dict.get('channel_id'),
                'channel_url': info_dict.get('channel_url'),
                'upload_date': info_dict.get('upload_date'),
                'duration': info_dict.get('duration'),
                'webpage_url': info_dict.get('webpage_url'),
                'description': info_dict.get('description'),
                'thumbnail': info_dict.get('thumbnail'),
                'was_live': info_dict.get('was_live'),
                'live_status': info_dict.get('live_status'),
            }
            return video_details
        
        except yt_dlp.utils.DownloadError as e:
            # Return a minimal dict on error to avoid breaking the loop
            print(f"\nError fetching metadata for {url}: {e}")
            return {}

def process_csv():
    """
    Processes a CSV file containing YouTube URLs and returns a list of dictionaries.
    """
    url_data = [] # list of dicts to hold processed data

    csv_path = Path(__file__).parent / 'video_urls.csv'
    if not csv_path.exists():
        print(f"CSV file not found at {csv_path}")
        return []

    with open(csv_path, mode='r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        data_dict = [row for row in reader]
    
    for d in data_dict:
        url = d.get('url')
        start_hour = int(d.get('start_hour'))
        start_min = int(d.get('start_min'))
        start_sec = int(d.get('start_sec'))
        end_hour = int(d.get('end_hour'))
        end_min = int(d.get('end_min'))
        end_sec = int(d.get('end_sec'))

        start_time = start_hour * 3600 + start_min * 60 + start_sec
        end_time = end_hour * 3600 + end_min * 60 + end_sec

        row = {
            'url': url,
            'start_time': start_time,
            'end_time': end_time,
        }

        url_data.append(row)
    
    return url_data

def process_video_links():
    print("Starting video processing...")
    video_data = process_csv() # get the list of dicts from CSV rows
    if not video_data:
        print("No videos found in CSV file. Exiting.")
        return

    print(f"Found {len(video_data)} videos to process.")
    db = SessionLocal() # db connector

    for i, row in enumerate(video_data, 1):
        print(f"\n--- Processing video {i} of {len(video_data)} ---")
        url = row.get('url')
        print(f"URL: {url}")

        existing_video = db.query(Video).filter(Video.webpage_url == url).first()

        if existing_video:
            print(f"Video '{existing_video.title}' already in database. Skipping.")
            continue
        else:
            print("Fetching video metadata...")
            video_metadata = get_video_metadata(url)
            if not video_metadata:
                print("Could not fetch metadata. Skipping.")
                continue

            new_video = Video(
                **video_metadata, # Unpack the metadata dictionary
                start_time=row.get('start_time'),
                end_time=row.get('end_time'),
                stage_1_status="completed"  # Metadata collection done
            )

            db.add(new_video)
            db.commit()
            print(f"Successfully added video '{new_video.title}' to the database.")


    db.close()
    print("\n--- Video processing complete. ---")


