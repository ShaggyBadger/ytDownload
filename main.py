import yt_dlp
from pathlib import Path

BASE_DIR = Path.cwd()
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)

with open("urlList.txt", "r") as file:
    urls = [
        line.strip()
        for line in file
        if line.strip()
        ]

ydl_opts = {
    'format': 'bestaudio/best',                # Best available audio
    'outtmpl': str(DOWNLOAD_DIR / '%(title)s.%(ext)s'),  # Output filename template
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',           # Extract audio using ffmpeg
        'preferredcodec': 'mp3',               # Set desired audio format (e.g., mp3)
        'preferredquality': '192',             # Set desired quality (kbps)
    }],
    'quiet': True,                            # Suppress output (optional)
    'noplaylist': True,                       # Download single video, not playlist (optional)
}

# === Download each URL ===
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for url in urls:
        try:
            print(f"Downloading: {url}")
            ydl.download([url])
            print(f"Finished downloading: {url}\n")
        except Exception as e:
            print(f"Error downloading {url}: {e}\n")