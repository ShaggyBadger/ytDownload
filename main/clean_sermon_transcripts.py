import glob
import os
import re

def clean_sermon_transcripts():
    """
    Finds all 'sermon_export.txt' files and removes extra blank lines from them.
    """
    sermon_files = glob.glob('main/downloads/**/sermon_export.txt', recursive=True)

    if not sermon_files:
        print("No 'sermon_export.txt' files found to clean.")
        return

    print(f"Found {len(sermon_files)} sermon export files to clean.")

    for file_path in sermon_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace two or more newlines with a single newline
            cleaned_content = re.sub(r'\n{2,}', '\n', content)

            if content != cleaned_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                print(f"Cleaned: {file_path}")
            else:
                print(f"Already clean: {file_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == '__main__':
    clean_sermon_transcripts()
