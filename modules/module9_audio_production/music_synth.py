"""Part of Module 9 — Audio Production (background music).

Procedural chord-pad BGM, standing in for the OpenAI architecture's royalty-free music
library / MusicGen — a slow sustained pad built from stacked sine waves whose root note,
interval (major/minor/dissonant), brightness, movement, and grit are all driven by the
scene's emotional_tone via mood.py. This is the "music matches the dream's mood" layer;
sfx_synth.py's ambience is the literal environmental texture (wind, rain, room tone).

Mixed in very quietly by module10's mixing.py, underneath both dialogue and ambience.
"""

import numpy as np
from pydub import AudioSegment

from .dsp import SAMPLE_RATE, linear_envelope, lowpass, sine, to_segment
from .mood import mood_params


def _semitone_ratio(semitones: float) -> float:
    return 2 ** (semitones / 12)


def _chord_layer(freq: float, n: int, sr: int, detune_cents: float, phase: float) -> np.ndarray:
    tone = sine(freq, n, sr, phase=phase)
    if detune_cents > 0:
        detuned = freq * (2 ** (detune_cents / 1200))
        tone = 0.5 * (tone + sine(detuned, n, sr, phase=phase))
    return tone


def generate_bgm(emotional_tone: str, duration_ms: int, seed: int | None = None) -> AudioSegment:
    """A slow sustained chord pad colored by emotional_tone. Root + fifth carry the drone,
    the third sets major/minor/dissonant character, tremolo/distortion add movement and
    grit for tenser moods. Long attack/release so it always feels like a sustained bed,
    never an abrupt clip, regardless of scene length.
    """
    if duration_ms <= 0:
        return AudioSegment.silent(duration=0, frame_rate=SAMPLE_RATE)
    n = int(SAMPLE_RATE * duration_ms / 1000)
    mood = mood_params(emotional_tone)

    root = mood.root_hz
    third = root * _semitone_ratio(mood.third_semitones)
    fifth = root * _semitone_ratio(mood.fifth_semitones)
    octave_up = root * 2
    sub = root / 2

    # Weighted toward root/third/fifth/octave (~150Hz-1.2kHz across moods) rather than the
    # sub layer — laptop and phone speakers reproduce that range; a 73-150Hz sub-bass layer
    # (the old version put 45% of the pad's energy there) is often nearly silent on real
    # playback hardware, which is exactly why the music wasn't cutting through the ambience
    # noise. The octave-up layer exists purely for presence/clarity on small speakers.
    pad = (
        0.12 * _chord_layer(sub, n, SAMPLE_RATE, 0.0, phase=0.0)
        + 0.32 * _chord_layer(root, n, SAMPLE_RATE, mood.detune_cents, phase=0.3)
        + 0.26 * _chord_layer(third, n, SAMPLE_RATE, mood.detune_cents, phase=0.6)
        + 0.20 * _chord_layer(fifth, n, SAMPLE_RATE, mood.detune_cents * 0.6, phase=0.9)
        + 0.14 * _chord_layer(octave_up, n, SAMPLE_RATE, mood.detune_cents * 0.4, phase=1.2)
    )

    # slow shimmer so the sustained chord doesn't sound static/synthetic
    shimmer = 1.0 + 0.15 * sine(0.05, n, SAMPLE_RATE)
    pad = pad * shimmer

    if mood.tremolo_hz > 0:
        movement = 1.0 + 0.3 * sine(mood.tremolo_hz, n, SAMPLE_RATE)
        pad = pad * movement

    pad = lowpass(pad, SAMPLE_RATE, mood.brightness_hz)

    if mood.distortion > 0:
        drive = 1 + mood.distortion * 3
        pad = np.tanh(pad * drive) / drive

    attack = min(n, int(SAMPLE_RATE * 1.5))
    release = min(n, int(SAMPLE_RATE * 1.5))
    pad = pad * linear_envelope(n, attack, release)

    return to_segment(pad * 0.5)
