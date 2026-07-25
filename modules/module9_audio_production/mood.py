"""Part of Module 9 — Audio Production.

Shared emotion -> musical-mood mapping used by both sfx_synth.py (to color ambience
brightness/movement) and music_synth.py (to pick the actual chord/tempo for the BGM bed).
Keeps "what does 'fear' sound like" defined in exactly one place instead of drifting
between the two generators.
"""

from typing import NamedTuple

_MOOD_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("fear", "dread", "tense", "tension", "anxious", "panic", "horror", "scared", "afraid"), "fear"),
    (("sad", "grief", "loss", "lonely", "melanchol", "sorrow", "despair", "heartbroken"), "sad"),
    (("anger", "rage", "fury", "furious", "irritat", "hostile"), "anger"),
    (("joy", "happy", "excite", "relief", "delight", "cheer", "triumphant", "elated"), "joy"),
    (("nostalg", "warm", "cozy", "loving", "tender"), "warm"),
    (("calm", "peace", "quiet", "still", "serene", "tranquil", "content"), "calm"),
    (("confus", "surreal", "disorient", "strange", "curious", "mysteri", "uncann", "eerie"), "mysterious"),
    (("surprise", "shock", "startl", "sudden", "awe"), "surprise"),
]


class MoodParams(NamedTuple):
    root_hz: float          # drone/pad root frequency
    third_semitones: int    # interval above root — major(4)/minor(3)/dissonant(1,6)
    fifth_semitones: int    # interval above root — usually 7 (perfect fifth) or 6 (tritone, unstable)
    brightness_hz: float    # lowpass cutoff — higher = brighter/clearer, lower = muffled/dark
    tremolo_hz: float       # amplitude-modulation rate — slow=calm swell, fast=anxious/aggressive pulse
    detune_cents: float     # how out-of-tune the doubled layer is — 0=pure/stable, high=unsettling
    distortion: float       # 0..1 soft-clip amount — aggression, used for anger


MOOD_PARAMS: dict[str, MoodParams] = {
    "joy":         MoodParams(261.63, 4, 7, 4200, 0.25, 0, 0.0),
    "warm":        MoodParams(220.00, 4, 7, 3000, 0.15, 2, 0.0),
    "calm":        MoodParams(196.00, 7, 12, 2400, 0.10, 0, 0.0),
    "sad":         MoodParams(174.61, 3, 7, 1100, 0.12, 4, 0.0),
    "mysterious":  MoodParams(207.65, 6, 10, 1800, 0.18, 6, 0.0),
    "fear":        MoodParams(164.81, 1, 6, 1600, 0.55, 10, 0.15),
    "anger":       MoodParams(146.83, 6, 7, 3200, 3.50, 12, 0.45),
    "surprise":    MoodParams(293.66, 4, 7, 5000, 0.70, 3, 0.0),
    "neutral":     MoodParams(220.00, 4, 7, 2200, 0.15, 0, 0.0),
}


def classify_mood(emotional_tone: str) -> str:
    text = (emotional_tone or "").lower()
    for keywords, mood in _MOOD_KEYWORDS:
        if any(k in text for k in keywords):
            return mood
    return "neutral"


def mood_params(emotional_tone: str) -> MoodParams:
    return MOOD_PARAMS[classify_mood(emotional_tone)]
