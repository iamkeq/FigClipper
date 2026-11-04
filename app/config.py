import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MAX_CLIPS = int(os.environ.get("MAX_CLIPS", "5"))
MIN_CLIP_LENGTH_S = float(os.environ.get("MIN_CLIP_LENGTH_S", "20"))
MAX_CLIP_LENGTH_S = float(os.environ.get("MAX_CLIP_LENGTH_S", "30"))
HARD_MAX_CLIPS = int(os.environ.get("HARD_MAX_CLIPS", "20"))

DATA_DIR = Path(os.environ.get("DATA_DIR", "data")).resolve()
UPLOADS_DIR = DATA_DIR / "uploads"
DOWNLOADS_DIR = DATA_DIR / "downloads"
CLIPS_DIR = DATA_DIR / "clips"
JOBS_FILE = DATA_DIR / "jobs.json"

for d in (UPLOADS_DIR, DOWNLOADS_DIR, CLIPS_DIR):
    d.mkdir(parents=True, exist_ok=True)
