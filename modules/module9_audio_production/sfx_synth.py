"""Part of Module 9 — Audio Production (SFX/ambience).

Procedural ambience + one-shot sound-effect synthesis using numpy/scipy only, in place of
the OpenAI architecture's Stable Audio Open/AudioGen/freesound.org options — this keeps the
pipeline free-tier and fully offline-capable with zero external SFX dependency.

Ambience is shaped by TWO independent signals: the cue's literal keywords (wind/rain/fire/
etc — picks *which* texture) and the scene's emotional_tone (picks brightness/movement/
distortion via mood.py — same texture reads calm vs. tense vs. aggressive depending on
mood). Background music (mood.py-driven chord pads) lives in music_synth.py, mixed in
separately by module10's mixing.py.
"""

import numpy as np
from pydub import AudioSegment

from .dsp import SAMPLE_RATE, bandpass, highpass, linear_envelope, lowpass, sine, to_segment, white_noise
from .mood import mood_params

# ---------------------------------------------------------------------------
# Ambience beds (looping-ish textures, generated directly at target length)
# ---------------------------------------------------------------------------

def _amb_wind(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    noise = bandpass(white_noise(n, rng), sr, 200, 1200)
    lfo = 0.5 + 0.5 * sine(0.15, n, sr)
    return noise * (0.4 + 0.6 * lfo)


def _amb_rain(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    hiss = bandpass(white_noise(n, rng), sr, 1500, 8000) * 0.6
    rumble = lowpass(white_noise(n, rng), sr, 300) * 0.3
    return hiss + rumble


def _amb_water(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    base = lowpass(white_noise(n, rng), sr, 500)
    swell = 0.5 + 0.5 * sine(0.08, n, sr)
    return base * (0.3 + 0.7 * swell)


def _amb_fire(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    crackle = bandpass(white_noise(n, rng), sr, 800, 5000)
    bursts = (rng.uniform(0, 1, n) > 0.9985).astype(float)
    bursts = np.convolve(bursts, np.ones(int(sr * 0.01)), mode="same")
    rumble = lowpass(white_noise(n, rng), sr, 200) * 0.3
    return crackle * bursts * 3 + rumble


def _amb_room_creak(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    base = lowpass(white_noise(n, rng), sr, 250) * 0.25
    return base


def _amb_crowd_city(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    noise = bandpass(white_noise(n, rng), sr, 300, 3000) * 0.35
    return noise


def _amb_default(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    return bandpass(white_noise(n, rng), sr, 150, 2500) * 0.3


_AMBIENCE_KEYWORDS: list[tuple[tuple[str, ...], "callable"]] = [
    (("wind", "gust", "breeze"), _amb_wind),
    (("rain", "storm", "thunder"), _amb_rain),
    (("water", "ocean", "wave", "river", "stream"), _amb_water),
    (("fire", "crackle", "flame", "campfire"), _amb_fire),
    (("creak", "wood", "echo", "house", "hall", "room", "attic", "corridor"), _amb_room_creak),
    (("crowd", "city", "street", "traffic", "market"), _amb_crowd_city),
]


def generate_ambience(
    prompt: str, duration_ms: int, emotional_tone: str = "", seed: int | None = None
) -> AudioSegment:
    if duration_ms <= 0:
        return AudioSegment.silent(duration=0, frame_rate=SAMPLE_RATE)
    rng = np.random.default_rng(seed)
    n = int(SAMPLE_RATE * duration_ms / 1000)
    prompt_l = prompt.lower()
    generator = _amb_default
    for keywords, gen in _AMBIENCE_KEYWORDS:
        if any(k in prompt_l for k in keywords):
            generator = gen
            break
    samples = generator(n, SAMPLE_RATE, rng)

    # Mood coloring — the same "wind" texture reads differently depending on scene emotion:
    # brighter/lighter for joy, muffled/dark for sadness, fast unstable tremolo for fear,
    # a rhythmic pulse + grit for anger. Keeps ambience from sounding identical scene to
    # scene just because two scenes happen to share a keyword like "wind" or "room".
    mood = mood_params(emotional_tone)
    samples = lowpass(samples, SAMPLE_RATE, mood.brightness_hz)
    if mood.tremolo_hz > 0:
        tremolo = 1.0 + 0.35 * sine(mood.tremolo_hz, n, SAMPLE_RATE)
        samples = samples * tremolo
    if mood.distortion > 0:
        drive = 1 + mood.distortion * 4
        samples = np.tanh(samples * drive) / drive

    fade = int(SAMPLE_RATE * 0.5)
    samples = samples * linear_envelope(n, fade, fade)
    return to_segment(samples * 0.6)


# ---------------------------------------------------------------------------
# One-shot cues
# ---------------------------------------------------------------------------

def _shot_door(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.7)
    t = np.linspace(0, 1, n)
    sweep_freq = 180 + 250 * t
    tone = np.sin(2 * np.pi * np.cumsum(sweep_freq) / sr)
    noise = bandpass(white_noise(n, rng), sr, 300, 1500) * 0.4
    env = linear_envelope(n, int(sr * 0.05), int(sr * 0.5))
    return (tone * 0.6 + noise) * env


def _shot_footstep(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.18)
    thud = lowpass(white_noise(n, rng), sr, 200)
    env = linear_envelope(n, int(sr * 0.005), int(sr * 0.15))
    return thud * env


def _shot_wind_gust(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 1.0)
    noise = bandpass(white_noise(n, rng), sr, 300, 1800)
    env = linear_envelope(n, int(sr * 0.3), int(sr * 0.5))
    return noise * env

def _shot_glass(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.4)
    shard = highpass(white_noise(n, rng), sr, 3000)
    env = linear_envelope(n, int(sr * 0.002), int(sr * 0.38))
    return shard * env


def _shot_bell(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 1.2)
    tone = sine(880, n, sr) + 0.5 * sine(1760, n, sr) + 0.25 * sine(2640, n, sr)
    env = np.exp(-np.linspace(0, 6, n))
    return tone * env


def _shot_thud(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.3)
    tone = sine(80, n, sr) * np.exp(-np.linspace(0, 8, n))
    noise = lowpass(white_noise(n, rng), sr, 150) * 0.3
    return tone + noise


def _shot_default(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.25)
    noise = bandpass(white_noise(n, rng), sr, 400, 4000)
    env = linear_envelope(n, int(sr * 0.005), int(sr * 0.22))
    return noise * env


_ONE_SHOT_KEYWORDS: list[tuple[tuple[str, ...], "callable"]] = [
    (("door", "creak", "hinge"), _shot_door),
    (("footstep", "step", "walk"), _shot_footstep),
    (("wind", "gust", "breeze"), _shot_wind_gust),
    (("glass", "shatter", "break"), _shot_glass),
    (("bell", "chime", "ring"), _shot_bell),
    (("thud", "impact", "drop", "knock"), _shot_thud),
]


def generate_one_shot(prompt: str, seed: int | None = None) -> AudioSegment:
    rng = np.random.default_rng(seed)
    prompt_l = prompt.lower()
    generator = _shot_default
    for keywords, gen in _ONE_SHOT_KEYWORDS:
        if any(k in prompt_l for k in keywords):
            generator = gen
            break
    samples = generator(SAMPLE_RATE, rng)
    return to_segment(samples * 0.7)
