import os
from pathlib import Path
from shared.models import Story, Scene, Line, Character
from modules.module9_audio_production.voice_generation import generate_voices

def test_qwen_voice():
    print("Testing Qwen3 TTS VoiceDesign integration...")
    
    # Mock story
    story = Story(
        title="Test Story",
        characters=[Character(id="C1", name="Alice", role="Protagonist")],
        scenes=[
            Scene(
                id=1,
                setting="A quiet forest",
                emotional_tone="mysterious",
                lines=[
                    Line(
                        speaker="C1",
                        text="Why did it have to be this way? I just wanted to say goodbye...",
                        performance_direction="Speak with deep sorrow, your voice cracking with tears, pausing to hold back a sob."
                    )
                ]
            )
        ]
    )
    
    tmp_dir = Path("./output/test_voices")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        story = generate_voices(story, tmp_dir)
        for scene in story.scenes:
            for line in scene.lines:
                print(f"Generated audio path: {line.audio_path}")
                print(f"Duration MS: {line.duration_ms}")
                if os.path.exists(line.audio_path):
                    print(f"File exists and size is: {os.path.getsize(line.audio_path)} bytes")
        print("Success!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error during voice generation: {e}")

if __name__ == "__main__":
    test_qwen_voice()
