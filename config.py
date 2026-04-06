import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ICLOUD_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
INPUT_DIR = Path.home() / "Library" / "Mobile Documents" / "NK37SPV8GQ~cn~winat~EasyVoice" / "Documents"
OUTPUT_DIR = BASE_DIR / "output"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".webm", ".flac", ".mp4", ".mpeg", ".mpga", ".aac"}

GEMINI_MODEL = "gemini-2.5-flash"

for d in [INPUT_DIR, OUTPUT_DIR]:
    d.mkdir(exist_ok=True)
