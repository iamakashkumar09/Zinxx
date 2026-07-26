"""Part of Module 9 — Audio Production (character voices).

Text-to-speech generation per line via Qwen3-TTS (VoiceDesign mode).
Uses the VoiceDesign model to map Module 8's natural language performance_direction 
directly into expressive, context-aware speech without relying on an API.
"""

import uuid
from pathlib import Path

import soundfile as sf
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from shared.models import Story

# Initialize Qwen3TTS lazily
_qwen_model = None

def _get_qwen_model():
    global _qwen_model
    if _qwen_model is None:
        from qwen_tts import Qwen3TTSModel
        import torch
        # float16 is GPU-only; CPU falls back to float32.
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        _qwen_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            device_map=device,
            dtype=dtype
        )
    return _qwen_model

def _is_valid_audio_file(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 256:
        return False
    try:
        AudioSegment.from_file(path, format="wav")
        return True
    except CouldntDecodeError:
        return False

def generate_voices(story: Story, tmp_dir: Path) -> Story:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    model = _get_qwen_model()

    line_paths: list[Path] = []
    
    # We assign speakers using the character ID as the 'speaker' name
    for scene in story.scenes:
        for line in scene.lines:
            
            direction = line.performance_direction or "Speak normally."
            
            # Using VoiceDesign which generates entirely new voices from instructions
            wavs, sr = model.generate_voice_design(
                text=line.text,
                language="English",
                instruct=direction,
            )
            
            # Save the WAV file using soundfile
            out_path = tmp_dir / f"line_{uuid.uuid4().hex}.wav"
            sf.write(str(out_path), wavs[0], sr)
            
            if not _is_valid_audio_file(out_path):
                raise RuntimeError(f"Failed to generate valid audio for line: {line.text}")
                
            line_paths.append(out_path)
            line.audio_path = str(out_path)

    # Process all paths to get duration
    idx = 0
    for scene in story.scenes:
        for line in scene.lines:
            audio = AudioSegment.from_file(line_paths[idx], format="wav")
            line.duration_ms = len(audio)
            idx += 1

    return story
