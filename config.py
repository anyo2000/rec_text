import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = INPUT_DIR / "output"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".webm", ".flac", ".mp4", ".mpeg", ".mpga"}

GEMINI_MODEL = "gemini-2.5-flash"
GPT_MODEL = "gpt-4o"

for d in [INPUT_DIR, OUTPUT_DIR]:
    d.mkdir(exist_ok=True)
