#!/bin/bash
# Update yt-dlp inside your Python virtual environment

set -e  # Exit on error

# Go to your project directory
cd ~/pyProjects/ytDownload

# Activate the virtual environment
source venvFiles/bin/activate

# Upgrade yt-dlp
python3 -m pip install -U yt-dlp

# Show version to confirm
python3 -m yt_dlp --version

# Deactivate environment
deactivate

echo "yt-dlp updated successfully."
