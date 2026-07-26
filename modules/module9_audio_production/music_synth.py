"""Part of Module 9 — Audio Production (background music).

Generates BGM using Stable Audio 3 Small Music. The scene's emotional_tone is
mapped to a rich descriptive text prompt which is passed to the AI model.

Replaces the old procedural numpy/scipy chord-pad synthesizer.
"""

from __future__ import annotations

from pydub import AudioSegment

from .mood import classify_mood
from .stable_audio_client import generate_music

# ---------------------------------------------------------------------------
# Emotion → music prompt mapping
# ---------------------------------------------------------------------------

_MOOD_MUSIC_PROMPTS: dict[str, str] = {
    "joy": (
        "uplifting orchestral music, bright major key, warm strings and piano, "
        "optimistic and triumphant, cinematic, moderately fast tempo"
    ),
    "warm": (
        "warm acoustic music, gentle guitar and soft piano, nostalgic and tender, "
        "slow tempo, intimate, cozy folk atmosphere"
    ),
    "calm": (
        "peaceful ambient music, slow sustained strings, gentle pads, "
        "serene and meditative, minimal, slow tempo, cinematic"
    ),
    "sad": (
        "melancholic orchestral music, slow minor key, cello and piano, "
        "sorrowful and introspective, sparse arrangement, cinematic sadness"
    ),
    "mysterious": (
        "dark mysterious ambient music, eerie sustained tones, dissonant pads, "
        "slow tempo, unsettling and surreal, dream-like, cinematic"
    ),
    "fear": (
        "tense horror music, low drones, dissonant strings, rising tension, "
        "dark and ominous, fast tremolo, cinematic suspense, no melody"
    ),
    "anger": (
        "intense aggressive music, heavy low brass, driving percussion, dissonant chords, "
        "fast and relentless, cinematic action, dark and powerful"
    ),
    "surprise": (
        "dramatic cinematic music, sudden dynamic shift, bright orchestral stab, "
        "ascending strings, building tension and release"
    ),
    "neutral": (
        "ambient cinematic music, slow sustained pads, neutral tone, "
        "understated and atmospheric, minimal, slow tempo"
    ),
}


def _build_music_prompt(emotional_tone: str) -> str:
    mood = classify_mood(emotional_tone)
    return _MOOD_MUSIC_PROMPTS.get(mood, _MOOD_MUSIC_PROMPTS["neutral"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_bgm(emotional_tone: str, duration_ms: int, seed: int | None = None) -> AudioSegment:
    """Generate background music for a scene using Stable Audio 3 Small Music.

    Args:
        emotional_tone: The scene's emotional tone (e.g. "fear", "calm joy").
        duration_ms: Target duration in milliseconds.
        seed: Unused (kept for API compatibility); Stable Audio uses its own sampling.

    Returns:
        AudioSegment with AI-generated music bed.

    Raises:
        RuntimeError: If Stable Audio generation fails.
    """
    if duration_ms <= 0:
        return AudioSegment.silent(duration=0)

    prompt = _build_music_prompt(emotional_tone)
    return generate_music(prompt, duration_ms)
