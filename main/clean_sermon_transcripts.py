import glob
import os
import re
from logger import setup_logger

logger = setup_logger(__name__)

def clean_sermon_transcripts():
    """
    Finds all 'sermon_export.txt' files and removes extra blank lines from them.
    """
    sermon_files = glob.glob('downloads/**/sermon_export.txt', recursive=True)

    if not sermon_files:
        logger.info("No 'sermon_export.txt' files found to clean.")
        return

    logger.info(f"Found {len(sermon_files)} sermon export files to clean.")

    for file_path in sermon_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace two or more newlines with a single newline
            cleaned_content = re.sub(r'\n{2,}', '\n', content)

            if content != cleaned_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                logger.info(f"Cleaned: {file_path}")
            else:
                logger.info(f"Already clean: {file_path}")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

if __name__ == '__main__':
    clean_sermon_transcripts()
