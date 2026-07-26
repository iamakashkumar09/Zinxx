"""Quick CLI sanity-check for Module 1 (dream understanding / story extraction) against
samples/sample_dreams.txt.

Run from the project root with the venv active:
    python scripts/test_story_extraction.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.module1_dream_understanding.story_extraction import extract_story  # noqa: E402

SAMPLES_PATH = PROJECT_ROOT / "samples" / "sample_dreams.txt"


def load_samples() -> list[tuple[str, str]]:
    raw = SAMPLES_PATH.read_text(encoding="utf-8")
    blocks = raw.split("### ")[1:]
    samples = []
    for block in blocks:
        label, _, body = block.partition("\n")
        samples.append((label.strip(), body.strip()))
    return samples


def main() -> None:
    samples = load_samples()
    passed = 0
    for label, text in samples:
        print(f"\n=== {label} ===")
        try:
            story = extract_story(text)
            print(f"OK  title={story.title!r} characters={len(story.characters)} scenes={len(story.scenes)}")
            passed += 1
        except ValueError as exc:
            print(f"EXPECTED-FAIL (empty input): {exc}")
            if not text:
                passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: {exc}")

    print(f"\n{passed}/{len(samples)} samples handled as expected.")


if __name__ == "__main__":
    main()
