"""Part of Module 9 — Audio Production.

Low-level numpy/scipy signal-generation primitives shared by sfx_synth.py (ambience/
one-shots) and music_synth.py (BGM pads) — kept in one place so both generators use
identical filtering/envelope/normalization behavior.
"""

import numpy as np
from pydub import AudioSegment
from scipy import signal as sp_signal

SAMPLE_RATE = 24000


def white_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(-1.0, 1.0, n)


def bandpass(x: np.ndarray, sr: int, low: float, high: float, order: int = 4) -> np.ndarray:
    nyq = sr / 2
    low = max(1, min(low, nyq - 1))
    high = max(low + 1, min(high, nyq - 1))
    sos = sp_signal.butter(order, [low / nyq, high / nyq], btype="band", output="sos")
    return sp_signal.sosfiltfilt(sos, x)


def lowpass(x: np.ndarray, sr: int, cutoff: float, order: int = 4) -> np.ndarray:
    nyq = sr / 2
    sos = sp_signal.butter(order, min(cutoff, nyq - 1) / nyq, btype="low", output="sos")
    return sp_signal.sosfiltfilt(sos, x)


def highpass(x: np.ndarray, sr: int, cutoff: float, order: int = 4) -> np.ndarray:
    nyq = sr / 2
    sos = sp_signal.butter(order, min(cutoff, nyq - 1) / nyq, btype="high", output="sos")
    return sp_signal.sosfiltfilt(sos, x)


def sine(freq: float, n: int, sr: int, phase: float = 0.0) -> np.ndarray:
    t = np.arange(n) / sr
    return np.sin(2 * np.pi * freq * t + phase)


def linear_envelope(n: int, attack: int, release: int) -> np.ndarray:
    env = np.ones(n)
    attack = min(attack, n)
    release = min(release, n)
    if attack > 0:
        env[:attack] = np.linspace(0, 1, attack)
    if release > 0:
        env[n - release :] = np.linspace(1, 0, release)
    return env


def normalize(x: np.ndarray, peak: float = 0.85) -> np.ndarray:
    max_val = np.max(np.abs(x)) if x.size else 0
    if max_val < 1e-9:
        return x
    return x / max_val * peak


def to_segment(x: np.ndarray, sr: int = SAMPLE_RATE) -> AudioSegment:
    x = normalize(x)
    pcm16 = (x * 32767).astype(np.int16)
    return AudioSegment(data=pcm16.tobytes(), sample_width=2, frame_rate=sr, channels=1)
