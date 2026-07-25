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
from pydub.exceptions import CouldntDecodeError

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

# top-emotion -> (rate_pct_at_full_intensity, pitch_hz_at_full_intensity)
#
# PITCH is the dangerous knob here, not rate: a listener identifies "who's speaking"
# largely by pitch, so a big pitch swing (we previously went up to +-32Hz) makes the same
# edge-tts voice sound like a different character from line to line — exactly the "why
# does the narrator keep changing voice" complaint. RATE (speaking faster/slower under
# stress, or slower when sad) reads as the same person being more agitated/calm, not as a
# different speaker, so it carries most of the emotional weight here; pitch is now just a
# light seasoning on top, capped low.
EMOTION_PROSODY = {
    "anger": (24, 8),
    "fear": (28, 7),
    "joy": (14, 6),
    "surprise": (22, 8),
    "sadness": (-20, -7),
    "disgust": (-8, -5),
    "neutral": (0, 0),
}

# Scores below the dominant emotion's raw confidence still get a floor of "effective"
# intensity so emotion isn't only audible on the single most-confident line, but kept
# modest — too high a floor means near-every line gets pushed hard, which is what made
# pitch swing wildly line-to-line last time.
_MIN_INTENSITY = 0.35
_MAX_ABS_RATE = 35
_MAX_ABS_PITCH = 12

# edge-tts's free endpoint occasionally drops a connection mid-write under the load of
# synthesizing every line in a story at once (asyncio.gather), leaving a truncated/corrupt
# mp3 that pydub can't decode later during mixing. Retrying + capping concurrency fixes
# both the cause (too many simultaneous connections) and the symptom (bad files).
# Microsoft's anti-abuse logic gets very angry if we open multiple WS connections at once,
# throwing "No audio was received". Dropped concurrency to 1 to fix this.
_MAX_SYNTH_ATTEMPTS = 5
_MAX_CONCURRENT_REQUESTS = 1


def assign_voices(story: Story) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for i, character in enumerate(story.characters):
        mapping[character.id] = VOICE_POOL[i % len(VOICE_POOL)]
    return mapping


def _prosody_for(emotion_scores: dict[str, float] | None) -> tuple[str, str]:
    if not emotion_scores:
        return "+0%", "+0Hz"
    top_emotion, score = max(emotion_scores.items(), key=lambda kv: kv[1])
    if top_emotion == "neutral":
        return "+0%", "+0Hz"

    rate_per, pitch_per = EMOTION_PROSODY.get(top_emotion, (0, 0))
    intensity = _MIN_INTENSITY + (1 - _MIN_INTENSITY) * score
    rate = max(-_MAX_ABS_RATE, min(_MAX_ABS_RATE, round(rate_per * intensity)))
    pitch = max(-_MAX_ABS_PITCH, min(_MAX_ABS_PITCH, round(pitch_per * intensity)))
    rate_str = f"{'+' if rate >= 0 else ''}{rate}%"
    pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
    return rate_str, pitch_str


def _is_valid_audio_file(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 256:
        return False
    try:
        AudioSegment.from_file(path, format="mp3")
        return True
    except CouldntDecodeError:
        return False


async def _synthesize_line(
    text: str, voice: str, rate: str, pitch: str, out_path: Path, semaphore: asyncio.Semaphore
) -> None:
    last_error: Exception | None = None
    for attempt in range(_MAX_SYNTH_ATTEMPTS):
        try:
            async with semaphore:
                communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
                await communicate.save(str(out_path))
            if _is_valid_audio_file(out_path):
                return
            last_error = RuntimeError("edge-tts wrote an empty/unreadable audio file")
        except Exception as exc:  # noqa: BLE001 - transient network hiccups, worth retrying
            last_error = exc
        out_path.unlink(missing_ok=True)
        if attempt < _MAX_SYNTH_ATTEMPTS - 1:
            await asyncio.sleep(1.5 * (attempt + 1))

    raise RuntimeError(
        f"Voice synthesis failed after {_MAX_SYNTH_ATTEMPTS} attempts for line {text[:60]!r}: {last_error}"
    ) from last_error


async def _synthesize_all(jobs: list[tuple[str, str, str, str, Path]]) -> None:
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)
    await asyncio.gather(
        *[
            _synthesize_line(text, voice, rate, pitch, path, semaphore)
            for text, voice, rate, pitch, path in jobs
        ]
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
