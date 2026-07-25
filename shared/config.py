import os
from pathlib import Path

from dotenv import load_dotenv

SHARED_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SHARED_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
EXAMPLES_DIR = OUTPUT_DIR / "examples"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

load_dotenv(PROJECT_ROOT / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

# Mixing constants shared between module9_audio_production/sound_cues.py (timing) and
# module10_mixing_timeline/mixing.py (assembly) — the contract between Module 9 and Module 10.
LINE_GAP_MS = 300
SCENE_CROSSFADE_MS = 500
AMBIENCE_GAIN_DB = -20
ONE_SHOT_GAIN_DB = -6

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
