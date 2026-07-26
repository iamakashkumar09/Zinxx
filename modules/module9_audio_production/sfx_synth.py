"""Part of Module 9 — Audio Production (SFX/ambience).

Generates ambient soundscapes and one-shot sound effects using Stable Audio 3
Small SFX. The existing keyword/category tables (ported from the procedural
synthesizers) are used to build rich, descriptive text prompts for the AI model
rather than driving numpy signal generators directly.

This keeps all the smart keyword-matching logic (multi-match, animal sounds,
ambience-vs-one-shot classification, etc.) while routing audio generation
through stabilityai/stable-audio-3-small-sfx for much higher quality output.
"""

from __future__ import annotations

import numpy as np
from pydub import AudioSegment

from .dsp import (
    SAMPLE_RATE, bandpass, highpass, linear_envelope, lowpass, sine,
    to_segment, white_noise,
)
from .mood import classify_mood, mood_params
from .stable_audio_client import generate_sfx

# ---------------------------------------------------------------------------
# Emotion → ambience coloring suffix (used in prompt enrichment)
# ---------------------------------------------------------------------------

_MOOD_AMBIENCE_SUFFIX: dict[str, str] = {
    "joy":        "bright and warm atmosphere, pleasant",
    "warm":       "cozy and intimate atmosphere",
    "calm":       "peaceful and serene, very quiet",
    "sad":        "lonely and desolate, muted and dark",
    "mysterious": "eerie and unsettling, strange tonal quality",
    "fear":       "tense and ominous, low rumble underneath, dread",
    "anger":      "harsh and aggressive, heavy and oppressive",
    "surprise":   "sharp and sudden, heightened energy",
    "neutral":    "neutral atmospheric texture",
}

# ---------------------------------------------------------------------------
# Ambience keyword → descriptive label for Stable Audio prompt building
# ---------------------------------------------------------------------------

_AMBIENCE_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("bell", "chime", "clock tower"),      "bells chiming at a distance, scattered, echoing"),
    (("dog", "bark", "woof"),               "distant dog barking repeatedly, outdoor ambience"),
    (("wolf", "howl"),                      "wolf howling in the distance, lonely wilderness"),
    (("cat", "meow", "yowl"),               "cat meowing intermittently, domestic ambience"),
    (("wind", "gust", "breeze"),            "wind blowing through trees, rustling leaves"),
    (("rain", "storm", "thunder"),          "heavy rain falling, thunder rumbling in the distance"),
    (("water", "ocean", "wave", "river", "stream"), "flowing water, gentle river stream ambience"),
    (("fire", "crackle", "flame", "campfire"), "fire crackling, warm campfire ambience"),
    (("insect", "cricket", "cicada", "bug"), "crickets and insects chirping at night"),
    (("bird", "forest", "jungle", "chirping"), "birds chirping in a forest, natural ambience"),
    (("creak", "wood", "echo", "house", "hall", "room", "attic", "corridor"), "quiet room ambience, creaking wood, indoor echo"),
    (("crowd", "city", "street", "traffic", "market"), "city street ambience, distant crowd noise, traffic"),
]

# ---------------------------------------------------------------------------
# One-shot keyword → descriptive label for Stable Audio prompt building
# ---------------------------------------------------------------------------

_ONE_SHOT_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("door", "creak", "hinge"),            "door creaking open slowly, isolated sound effect"),
    (("dog", "bark", "woof"),               "dog barking twice, sharp isolated sound effect"),
    (("bird", "chirp", "tweet"),            "bird chirping, bright isolated sound effect"),
    (("wolf", "howl"),                      "wolf howling, long isolated sound effect"),
    (("cat", "meow", "yowl"),               "cat meowing, isolated sound effect"),
    (("footstep", "step", "walk"),          "footstep on hard floor, isolated sound effect"),
    (("wind", "gust", "breeze"),            "sudden wind gust, isolated sound effect"),
    (("glass", "shatter", "break"),         "glass shattering, sharp isolated sound effect"),
    (("bell", "chime", "ring"),             "bell chime ringing, clear isolated sound effect"),
    (("thud", "impact", "drop", "knock"),   "heavy thud impact, isolated sound effect"),
]

_DEFAULT_AMBIENCE_LABEL = "ambient room tone, neutral background sound"
_DEFAULT_ONE_SHOT_LABEL = "short sound effect, isolated, sharp transient"


# ---------------------------------------------------------------------------
# Keyword matching — same multi-match logic from the original implementation
# ---------------------------------------------------------------------------

def _matched_labels(
    prompt_l: str,
    table: list[tuple[tuple[str, ...], str]],
    default: str,
) -> list[str]:
    """Return every matching descriptive label whose keywords appear in the prompt.

    Returns all matches (not just the first) so a cue like 'dog barking, answered
    by a wolf' produces labels for both sounds instead of silently dropping one.
    Falls back to default when nothing matches.
    """
    matched = []
    for keywords, label in table:
        if any(k in prompt_l for k in keywords) and label not in matched:
            matched.append(label)
    return matched or [default]


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_ambience_prompt(prompt: str, emotional_tone: str) -> str:
    """Combine keyword-matched labels with mood coloring into a single rich prompt."""
    prompt_l = prompt.lower()
    labels = _matched_labels(prompt_l, _AMBIENCE_KEYWORDS, _DEFAULT_AMBIENCE_LABEL)
    sound_desc = ", ".join(labels)

    mood = classify_mood(emotional_tone)
    suffix = _MOOD_AMBIENCE_SUFFIX.get(mood, _MOOD_AMBIENCE_SUFFIX["neutral"])

    return f"{sound_desc}, {suffix}, ambient sound design, field recording quality, seamless loop"


def _build_one_shot_prompt(prompt: str) -> str:
    """Combine keyword-matched labels into a one-shot SFX prompt.

    When multiple sounds are named (e.g. 'dog barking, answered by a wolf'),
    all matched labels are joined so the model generates both in sequence.
    """
    prompt_l = prompt.lower()
    labels = _matched_labels(prompt_l, _ONE_SHOT_KEYWORDS, _DEFAULT_ONE_SHOT_LABEL)
    sound_desc = ", ".join(labels)
    return f"{sound_desc}, high quality audio, clean recording"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_ambience(
    prompt: str, duration_ms: int, emotional_tone: str = "", seed: int | None = None
) -> AudioSegment:
    """Generate an ambient soundscape using Stable Audio 3 Small SFX.

    The keyword tables from the original procedural synthesizer are used to
    build a rich descriptive prompt for the AI model. Mood coloring from
    emotional_tone is appended as a suffix to shape the emotional quality of
    the generated sound.

    Args:
        prompt: LLM-generated description of the ambience (e.g. "dark forest at night").
        duration_ms: Target duration in milliseconds.
        emotional_tone: Scene's emotional tone for mood coloring.
        seed: Unused (kept for API compatibility).

    Returns:
        AudioSegment with AI-generated ambience, trimmed/padded to duration_ms.

    Raises:
        RuntimeError: If Stable Audio generation fails.
    """
    if duration_ms <= 0:
        return AudioSegment.silent(duration=0)

    enriched_prompt = _build_ambience_prompt(prompt, emotional_tone)
    print(f"[SFX] Ambience prompt: {enriched_prompt!r}")
    return generate_sfx(enriched_prompt, duration_ms)


def generate_one_shot(prompt: str, seed: int | None = None) -> AudioSegment:
    """Generate a one-shot sound effect using Stable Audio 3 Small SFX.

    Multi-sound cues (e.g. 'dog barking, answered by a wolf') are handled by
    joining all matched keyword labels so the model generates both in sequence,
    preserving the original multi-match behavior from the procedural synthesizer.

    Args:
        prompt: LLM-generated description of the sound (e.g. "door creaking open").
        seed: Unused (kept for API compatibility).

    Returns:
        AudioSegment with AI-generated one-shot SFX (natural model length).

    Raises:
        RuntimeError: If Stable Audio generation fails.
    """
    enriched_prompt = _build_one_shot_prompt(prompt)
    print(f"[SFX] One-shot prompt: {enriched_prompt!r}")
    # duration_ms=0 → model picks natural length (trimmed to minimum 1s in client)
    return generate_sfx(enriched_prompt, duration_ms=0)
