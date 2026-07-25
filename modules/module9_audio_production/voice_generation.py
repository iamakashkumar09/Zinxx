"""Part of Module 9 — Audio Production (character voices).

Text-to-speech generation per line via edge-tts (free, no API key — used instead of
gpt-4o-mini-tts/tts-1-hd from the OpenAI-based architecture doc), with a consistent voice
per character and prosody (rate/pitch) nudged by that line's emotion scores from Module 8.
"""

import asyncio
import uuid
from pathlib import Path

import edge_tts
from pydub import AudioSegment

from shared.models import Story

VOICE_POOL = [
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-US-AriaNeural",
    "en-GB-RyanNeural",
    "en-GB-SoniaNeural",
    "en-AU-NatashaNeural",
    "en-US-DavisNeural",
    "en-IE-ConnorNeural",
]

# top-emotion -> (rate_pct_per_intensity, pitch_hz_per_intensity)
EMOTION_PROSODY = {
    "anger": (15, 20),
    "fear": (20, 15),
    "joy": (10, 10),
    "surprise": (15, 15),
    "sadness": (-15, -20),
    "disgust": (-5, -10),
    "neutral": (0, 0),
}


def assign_voices(story: Story) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for i, character in enumerate(story.characters):
        mapping[character.id] = VOICE_POOL[i % len(VOICE_POOL)]
    return mapping


def _prosody_for(emotion_scores: dict[str, float] | None) -> tuple[str, str]:
    if not emotion_scores:
        return "+0%", "+0Hz"
    top_emotion, score = max(emotion_scores.items(), key=lambda kv: kv[1])
    rate_per, pitch_per = EMOTION_PROSODY.get(top_emotion, (0, 0))
    rate = round(rate_per * score)
    pitch = round(pitch_per * score)
    rate_str = f"{'+' if rate >= 0 else ''}{rate}%"
    pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
    return rate_str, pitch_str


async def _synthesize_line(text: str, voice: str, rate: str, pitch: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(str(out_path))


async def _synthesize_all(jobs: list[tuple[str, str, str, str, Path]]) -> None:
    await asyncio.gather(
        *[_synthesize_line(text, voice, rate, pitch, path) for text, voice, rate, pitch, path in jobs]
    )


def generate_voices(story: Story, tmp_dir: Path) -> Story:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    voice_map = assign_voices(story)

    jobs: list[tuple[str, str, str, str, Path]] = []
    line_paths: list[Path] = []
    for scene in story.scenes:
        for line in scene.lines:
            voice = voice_map.get(line.speaker, VOICE_POOL[0])
            rate, pitch = _prosody_for(line.emotion_scores)
            out_path = tmp_dir / f"line_{uuid.uuid4().hex}.mp3"
            jobs.append((line.text, voice, rate, pitch, out_path))
            line_paths.append(out_path)
            line.audio_path = str(out_path)

    asyncio.run(_synthesize_all(jobs))

    idx = 0
    for scene in story.scenes:
        for line in scene.lines:
            audio = AudioSegment.from_file(line_paths[idx], format="mp3")
            line.duration_ms = len(audio)
            idx += 1

    return story
