import asyncio
import os
import sys
from dotenv import load_dotenv

# Force UTF-8 for console prints
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

from shared.models import Story, Scene, Line, SoundCue, Character
from modules import module9_audio_production as module9
from modules import module10_mixing_timeline as module10
from shared.config import OUTPUT_DIR
import uuid
import shutil

def main():
    print("=== Testing Module 9 & 10 (Audio + Mixing) ===")
    
    # Minimal mock story
    story = Story(
        title="Module 10 Test",
        logline="A quick test for mixing.",
        characters=[
            Character(id="char_1", name="Narrator", role="Narrator", short_bio="The narrator.")
        ],
        scenes=[
            Scene(
                id=1,
                setting="A quiet room.",
                emotional_tone="calm",
                characters=["char_1"],
                lines=[
                    Line(speaker="char_1", text="This is a test of the mixing module.", emotion_scores={"neutral": 1.0}, performance_direction="Speak calmly.")
                ],
                sound_cues=[
                    SoundCue(type="one-shot", position="before line 1", prompt="bell chime ringing, clear isolated sound effect")
                ]
            )
        ]
    )
    
    tmp_dir = OUTPUT_DIR / "tmp" / uuid.uuid4().hex
    try:
        print("--- Running Module 9 (Audio Production) ---")
        story = module9.process(story, tmp_dir)
        print("Audio production complete.")
        
        print("--- Running Module 10 (Mixing Timeline) ---")
        final_path = module10.process(story, OUTPUT_DIR)
        print(f"Success! Mixed audio saved to: {final_path}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
