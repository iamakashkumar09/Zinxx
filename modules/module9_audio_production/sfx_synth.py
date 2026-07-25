"""Part of Module 9 — Audio Production (SFX/ambience).

Procedural ambience + one-shot sound-effect synthesis using numpy/scipy only, in place of
the OpenAI architecture's Stable Audio Open/AudioGen/freesound.org options — this keeps the
pipeline free-tier and fully offline-capable with zero external SFX dependency. No
background-music generation in this build (Architecture.md's Module 9 also covers music).
"""

import numpy as np
from pydub import AudioSegment
from scipy import signal as sp_signal

SAMPLE_RATE = 24000


def _white_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(-1.0, 1.0, n)


def _bandpass(x: np.ndarray, sr: int, low: float, high: float, order: int = 4) -> np.ndarray:
    nyq = sr / 2
    low = max(1, min(low, nyq - 1))
    high = max(low + 1, min(high, nyq - 1))
    sos = sp_signal.butter(order, [low / nyq, high / nyq], btype="band", output="sos")
    return sp_signal.sosfiltfilt(sos, x)


def _lowpass(x: np.ndarray, sr: int, cutoff: float, order: int = 4) -> np.ndarray:
    nyq = sr / 2
    sos = sp_signal.butter(order, min(cutoff, nyq - 1) / nyq, btype="low", output="sos")
    return sp_signal.sosfiltfilt(sos, x)


def _highpass(x: np.ndarray, sr: int, cutoff: float, order: int = 4) -> np.ndarray:
    nyq = sr / 2
    sos = sp_signal.butter(order, min(cutoff, nyq - 1) / nyq, btype="high", output="sos")
    return sp_signal.sosfiltfilt(sos, x)


def _sine(freq: float, n: int, sr: int, phase: float = 0.0) -> np.ndarray:
    t = np.arange(n) / sr
    return np.sin(2 * np.pi * freq * t + phase)


def _linear_envelope(n: int, attack: int, release: int) -> np.ndarray:
    env = np.ones(n)
    attack = min(attack, n)
    release = min(release, n)
    if attack > 0:
        env[:attack] = np.linspace(0, 1, attack)
    if release > 0:
        env[n - release :] = np.linspace(1, 0, release)
    return env


def _normalize(x: np.ndarray, peak: float = 0.85) -> np.ndarray:
    max_val = np.max(np.abs(x)) if x.size else 0
    if max_val < 1e-9:
        return x
    return x / max_val * peak


def _to_segment(x: np.ndarray, sr: int = SAMPLE_RATE) -> AudioSegment:
    x = _normalize(x)
    pcm16 = (x * 32767).astype(np.int16)
    return AudioSegment(
        data=pcm16.tobytes(), sample_width=2, frame_rate=sr, channels=1
    )


# ---------------------------------------------------------------------------
# Ambience beds (looping-ish textures, generated directly at target length)
# ---------------------------------------------------------------------------

def _amb_wind(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    noise = _bandpass(_white_noise(n, rng), sr, 200, 1200)
    lfo = 0.5 + 0.5 * _sine(0.15, n, sr)
    return noise * (0.4 + 0.6 * lfo)


def _amb_rain(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    hiss = _bandpass(_white_noise(n, rng), sr, 1500, 8000) * 0.6
    rumble = _lowpass(_white_noise(n, rng), sr, 300) * 0.3
    return hiss + rumble


def _amb_water(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    base = _lowpass(_white_noise(n, rng), sr, 500)
    swell = 0.5 + 0.5 * _sine(0.08, n, sr)
    return base * (0.3 + 0.7 * swell)


def _amb_fire(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    crackle = _bandpass(_white_noise(n, rng), sr, 800, 5000)
    bursts = (rng.uniform(0, 1, n) > 0.9985).astype(float)
    bursts = np.convolve(bursts, np.ones(int(sr * 0.01)), mode="same")
    rumble = _lowpass(_white_noise(n, rng), sr, 200) * 0.3
    return crackle * bursts * 3 + rumble


def _amb_room_creak(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    base = _lowpass(_white_noise(n, rng), sr, 250) * 0.25
    return base


def _amb_crowd_city(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    noise = _bandpass(_white_noise(n, rng), sr, 300, 3000) * 0.35
    return noise


def _amb_default(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    return _bandpass(_white_noise(n, rng), sr, 150, 2500) * 0.3


_AMBIENCE_KEYWORDS: list[tuple[tuple[str, ...], "callable"]] = [
    (("wind", "gust", "breeze"), _amb_wind),
    (("rain", "storm", "thunder"), _amb_rain),
    (("water", "ocean", "wave", "river", "stream"), _amb_water),
    (("fire", "crackle", "flame", "campfire"), _amb_fire),
    (("creak", "wood", "echo", "house", "hall", "room", "attic", "corridor"), _amb_room_creak),
    (("crowd", "city", "street", "traffic", "market"), _amb_crowd_city),
]


def generate_ambience(prompt: str, duration_ms: int, seed: int | None = None) -> AudioSegment:
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
    fade = int(SAMPLE_RATE * 0.5)
    samples = samples * _linear_envelope(n, fade, fade)
    return _to_segment(samples * 0.6)


# ---------------------------------------------------------------------------
# One-shot cues
# ---------------------------------------------------------------------------

def _shot_door(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.7)
    t = np.linspace(0, 1, n)
    sweep_freq = 180 + 250 * t
    tone = np.sin(2 * np.pi * np.cumsum(sweep_freq) / sr)
    noise = _bandpass(_white_noise(n, rng), sr, 300, 1500) * 0.4
    env = _linear_envelope(n, int(sr * 0.05), int(sr * 0.5))
    return (tone * 0.6 + noise) * env


def _shot_footstep(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.18)
    thud = _lowpass(_white_noise(n, rng), sr, 200)
    env = _linear_envelope(n, int(sr * 0.005), int(sr * 0.15))
    return thud * env


def _shot_wind_gust(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 1.0)
    noise = _bandpass(_white_noise(n, rng), sr, 300, 1800)
    env = _linear_envelope(n, int(sr * 0.3), int(sr * 0.5))
    return noise * env

def _shot_glass(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.4)
    shard = _highpass(_white_noise(n, rng), sr, 3000)
    env = _linear_envelope(n, int(sr * 0.002), int(sr * 0.38))
    return shard * env


def _shot_bell(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 1.2)
    tone = _sine(880, n, sr) + 0.5 * _sine(1760, n, sr) + 0.25 * _sine(2640, n, sr)
    env = np.exp(-np.linspace(0, 6, n))
    return tone * env


def _shot_thud(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.3)
    tone = _sine(80, n, sr) * np.exp(-np.linspace(0, 8, n))
    noise = _lowpass(_white_noise(n, rng), sr, 150) * 0.3
    return tone + noise


def _shot_default(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.25)
    noise = _bandpass(_white_noise(n, rng), sr, 400, 4000)
    env = _linear_envelope(n, int(sr * 0.005), int(sr * 0.22))
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
    return _to_segment(samples * 0.7)
