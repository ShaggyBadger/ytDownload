from numpy import save
import yt_dlp
import pandas as pd
from pathlib import Path
from pydub import AudioSegment

def get_intel_from_csv(csv_path):
    """Read video information from a CSV file, filter for unprocessed videos,
    and return a list of dictionaries containing video details.

    Args:
        csv_path (Path): The path to the CSV file.

    Returns:
        list: A list of dictionaries, where each dictionary contains the
              'url', 'start_time', and 'end_time' of an unprocessed video.
    """
    df = pd.read_csv(csv_path)
    unprocessed_videos = df[df['processed'].isnull() | (df['processed'] == False)]
    return unprocessed_videos[['url', 'start_time', 'end_time']].to_dict('records')

def get_audio_clip(url, download_dir):
    """Downloads the audio from a YouTube video as an MP3 file.

    Args:
        url (str): The URL of the YouTube video.
        download_dir (Path): The directory to save the downloaded audio.

    Returns:
        tuple: A tuple containing the path to the downloaded audio file
               and the video ID, or (None, None) on error.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(download_dir / '%(id)s.%(ext)s'),
        'keepvideo': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            audio_path = download_dir / f"{video_id}.mp3"
            return audio_path, video_id
        except yt_dlp.utils.DownloadError:
            # Handle download errors, maybe log them
            return None, None

def trim_audio_clip(input_path, output_path, start_time, end_time):
    """Trims an audio file to the specified start and end times.

    Args:
        input_path (Path): The path to the input audio file.
        output_path (Path): The path to save the trimmed audio file.
        start_time (float): The start time in seconds.
        end_time (float): The end time in seconds.
    """
    audio = AudioSegment.from_file(input_path)
    trimmed_audio = audio[start_time * 1000:end_time * 1000]  # pydub works in milliseconds
    trimmed_audio.export(output_path, format="mp3")

def update_csv(csv_path, url, video_id, file_name, file_path):
    """Updates the CSV file with processing information for a video.

    Args:
        csv_path (Path): The path to the CSV file.
        url (str): The URL of the processed video.
        video_id (str): The YouTube video ID.
        file_name (str): The name of the processed file.
        file_path (str): The path to the processed file.
    """
    df = pd.read_csv(csv_path)
    # Find the row to update based on the URL
    row_index = df.index[df['url'] == url].tolist()
    if row_index:
        idx = row_index[0]
        df.loc[idx, 'id'] = video_id
        df.loc[idx, 'processed'] = True
        df.loc[idx, 'file_name'] = file_name
        df.loc[idx, 'file_path'] = str(file_path)
        df.to_csv(csv_path, index=False)

def main():
    BASE_DIR = Path.cwd()
    AUDIO_DIR = BASE_DIR / "downloads" / "audio"
    AUDIO_DIR.mkdir(exist_ok=True, parents=True)
    CSV_PATH = BASE_DIR / "video_info.csv"

    intel = get_intel_from_csv(CSV_PATH)
    for row in intel:
        url = row.get('url')
        start_time = row.get('start_time')
        end_time = row.get('end_time')
        
        audio_path, video_id = get_audio_clip(url, AUDIO_DIR)

        if audio_path and video_id and audio_path.exists():
            trim_audio_clip(
                input_path=audio_path,
                output_path=audio_path,
                start_time=start_time,
                end_time=end_time
            )
            
            file_name = audio_path.name
            
            update_csv(
                csv_path=CSV_PATH,
                url=url,
                video_id=video_id,
                file_name=file_name,
                file_path=audio_path
            )

if __name__ == "__main__":
    main()