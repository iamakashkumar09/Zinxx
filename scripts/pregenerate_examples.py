"""Pre-generate 2-3 polished example outputs for a demo-safe fallback.

Run this once (with GROQ_API_KEY set and internet access) before a live demo:
    python scripts/pregenerate_examples.py

Writes audio + a manifest JSON (story + audio_url) per example into output/examples/,
which the frontend's "Load a pre-made example" buttons read from /api/examples.

Exercises the full built pipeline end to end, same chain as app.py:
    module1_dream_understanding -> module8_audio_direction
        -> module9_audio_production -> module10_mixing_timeline
"""

import json
import shutil
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules import module1_dream_understanding as module1  # noqa: E402
from modules import module8_audio_direction as module8  # noqa: E402
from modules import module9_audio_production as module9  # noqa: E402
from modules import module10_mixing_timeline as module10  # noqa: E402
from shared.config import EXAMPLES_DIR, OUTPUT_DIR  # noqa: E402

DEMO_DREAMS = [
    "I kept opening doors in a house I didn't recognize, but none of them led where they "
    "should. I was looking for my sister, and I could hear her calling from somewhere, but "
    "every room was empty. The walls felt like they were breathing.",
    "I was standing on a beach at night, completely alone, and the waves kept getting "
    "louder. I felt calm at first, just watching the water, but then a strange fear crept "
    "in as the tide started rising toward me faster than it should.",
    "Someone was following me through a parking garage, and I could hear footsteps echoing "
    "but never see who it was. I tried to get to my car but couldn't remember where I "
    "parked. Then a door slammed somewhere above me and I woke up with my heart pounding.",
]


def build_example(dream_text: str, index: int) -> None:
    print(f"\n[{index}] Module 1 — dream understanding...")
    story = module1.process(dream_text)

    print(f"[{index}] Module 8 — audio direction (emotion + performance)...")
    story = module8.process(story)

    tmp_dir = OUTPUT_DIR / "tmp" / uuid.uuid4().hex
    print(f"[{index}] Module 9 — audio production (voices + SFX)...")
    story = module9.process(story, tmp_dir)

    print(f"[{index}] Module 10 — mixing & timeline...")
    final_path = module10.process(story, EXAMPLES_DIR)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    manifest = {
        "story": json.loads(story.model_dump_json()),
        "audio_url": f"/output/examples/{final_path.name}",
    }
    manifest_path = EXAMPLES_DIR / f"example_{index}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[{index}] Saved {manifest_path.name} -> {final_path.name}")


def main() -> None:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for i, dream in enumerate(DEMO_DREAMS, start=1):
        try:
            build_example(dream, i)
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}] FAILED: {exc}")


if __name__ == "__main__":
    main()
