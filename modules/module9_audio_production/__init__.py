"""Module 9 — Audio Production.

Job (per Architecture.md): TTS + ambience + foley. In this build: edge-tts for character
voices (free, in place of gpt-4o-mini-tts/tts-1-hd) and procedural numpy/scipy synthesis
for ambience/one-shot SFX (free and offline, in place of Stable Audio Open/AudioGen/
freesound.org — no background music generation in this build).

Public API: process(story, tmp_dir) -> Story

Input: the Story produced by Module 8 (audio_direction) — every Line already has
emotion_scores + performance_direction. Output: the same Story with every Line's
audio_path/duration_ms filled in, and every one-shot SoundCue's position_ms resolved —
this becomes Module 10's (mixing_timeline) input.
"""

from pathlib import Path

from modules.module9_audio_production import sound_cues, voice_generation
from shared.models import Story


def process(story: Story, tmp_dir: Path) -> Story:
    story = voice_generation.generate_voices(story, tmp_dir)
    story = sound_cues.resolve_positions(story)
    return story
