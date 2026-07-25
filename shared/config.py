import os
from pathlib import Path

from dotenv import load_dotenv

SHARED_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SHARED_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
EXAMPLES_DIR = OUTPUT_DIR / "examples"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

load_dotenv(PROJECT_ROOT / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4")

# Module 9 (Audio Production) — Stable Audio 3 Small models from Hugging Face.
# Requires: pip install stable-audio-tools torchaudio
# First run downloads ~500 MB per model, cached in ~/.cache/huggingface/hub/
STABLE_AUDIO_MUSIC_MODEL = os.environ.get(
    "STABLE_AUDIO_MUSIC_MODEL", "stabilityai/stable-audio-3-small-music"
)
STABLE_AUDIO_SFX_MODEL = os.environ.get(
    "STABLE_AUDIO_SFX_MODEL", "stabilityai/stable-audio-3-small-sfx"
)

# Module 2 (Dream Graph) — local SQLite file, zero setup (no server/URL/port/password).
# Override via DREAM_DB_URL in .env only if you deliberately want a different backend.
DREAM_DB_URL = os.environ.get("DREAM_DB_URL", f"sqlite+aiosqlite:///{(OUTPUT_DIR / 'dream_graph.db').as_posix()}")

# Mixing constants shared between module9_audio_production/sound_cues.py (timing) and
# module10_mixing_timeline/mixing.py (assembly) — the contract between Module 9 and Module 10.
LINE_GAP_MS = 300
SCENE_CROSSFADE_MS = 500
AMBIENCE_GAIN_DB = -21  # noise-based texture — supporting layer, not the dominant sound
ONE_SHOT_GAIN_DB = -6
# BGM was originally -25dB and, combined with most of its energy sitting in a near-
# inaudible sub-bass range (since fixed in music_synth.py), was effectively silent on real
# speakers — which is exactly why the mix read as "just ambience hiss, no music." -16dB
# with the rebalanced mid-range-heavy chord pad is the level where it's actually audible
# as music without competing with dialogue.
BGM_GAIN_DB = -16

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
