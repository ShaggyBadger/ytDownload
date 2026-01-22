from pathlib import Path
from rich import box

# Define the absolute path to the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define other configurations relative to the project root
DATABASE_PATH = PROJECT_ROOT / "project_database.db"
SERVER_URL = 'http://192.168.68.66:5000'

BOX_STYLE = box.MINIMAL_DOUBLE_HEAD

"""
rich box options:
box_options = [
    box.SQUARE,
    box.ROUNDED,
    box.MINIMAL,
    box.MINIMAL_DOUBLE_HEAD,
    box.DOUBLE,          # thick, heavy borders
    box.HEAVY,           # very bold borders
]
"""