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


def _random_chirp_bed(
    n: int, sr: int, rng: np.random.Generator, base_low: float, base_high: float,
    base_gain: float, chirp_freq: float, chirp_gain: float, chirp_density: float, chirp_len_s: float,
) -> np.ndarray:
    """Shared shape for animal-texture ambience: a quiet noise floor with scattered short
    tonal chirps sprinkled on top (crickets, distant birds) — density/pitch/length tuned
    per-species by the caller."""
    base = bandpass(white_noise(n, rng), sr, base_low, base_high) * base_gain
    hits = (rng.uniform(0, 1, n) > (1 - chirp_density)).astype(float)
    hits = np.convolve(hits, np.ones(int(sr * chirp_len_s)), mode="same")
    hits = np.clip(hits, 0, 1)
    tone = sine(chirp_freq, n, sr) * hits * chirp_gain
    return base + tone


def _amb_insects(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    return _random_chirp_bed(n, sr, rng, 3000, 8000, 0.06, 4500, 0.35, 0.0006, 0.02)


def _amb_forest_birds(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    base = _random_chirp_bed(n, sr, rng, 200, 1500, 0.12, 2800, 0.4, 0.001, 0.05)
    # a second, lower species mixed in so it doesn't read as one repeating bird
    base += _random_chirp_bed(n, sr, rng, 200, 1500, 0.0, 1900, 0.3, 0.0007, 0.04)
    return base


_AMBIENCE_KEYWORDS: list[tuple[tuple[str, ...], "callable"]] = [
    (("wind", "gust", "breeze"), _amb_wind),
    (("rain", "storm", "thunder"), _amb_rain),
    (("water", "ocean", "wave", "river", "stream"), _amb_water),
    (("fire", "crackle", "flame", "campfire"), _amb_fire),
    (("insect", "cricket", "cicada", "bug"), _amb_insects),
    (("bird", "forest", "jungle", "chirping"), _amb_forest_birds),
    (("creak", "wood", "echo", "house", "hall", "room", "attic", "corridor"), _amb_room_creak),
    (("crowd", "city", "street", "traffic", "market"), _amb_crowd_city),
]


def _matched_generators(prompt_l: str, table: list[tuple[tuple[str, ...], "callable"]], default) -> list:
    """Returns every distinct generator whose keywords appear in the prompt, not just the
    first — a cue like "dog barking, answered by a wolf" names two distinct sound sources,
    and picking only the first match (a real bug found in testing) silently drops the other
    entirely instead of just being a suboptimal pick."""
    matched = []
    for keywords, gen in table:
        if any(k in prompt_l for k in keywords) and gen not in matched:
            matched.append(gen)
    return matched or [default]


def generate_ambience(
    prompt: str, duration_ms: int, emotional_tone: str = "", seed: int | None = None
) -> AudioSegment:
    if duration_ms <= 0:
        return AudioSegment.silent(duration=0, frame_rate=SAMPLE_RATE)
    rng = np.random.default_rng(seed)
    n = int(SAMPLE_RATE * duration_ms / 1000)
    prompt_l = prompt.lower()
    generators = _matched_generators(prompt_l, _AMBIENCE_KEYWORDS, _amb_default)
    samples = np.zeros(n)
    for gen in generators:
        samples = samples + gen(n, SAMPLE_RATE, rng) / len(generators)

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


# ---------------------------------------------------------------------------
# Animal one-shots — pitch-contour + noise-texture synthesis, no samples needed.
# Each animal's "voice" is a distinct frequency contour: a bark is a short falling
# pitch + growl noise, a howl is a slow rise-then-fall with vibrato, a chirp is a fast
# high warble, a meow is a rising-then-falling glide. That contour is what makes each
# one recognizable as *that* animal rather than just another burst of noise.
# ---------------------------------------------------------------------------

def _pitch_sweep(freq_contour: np.ndarray, sr: int) -> np.ndarray:
    return np.sin(2 * np.pi * np.cumsum(freq_contour) / sr)


def _shot_dog_bark(sr: int, rng: np.random.Generator) -> np.ndarray:
    def burst() -> np.ndarray:
        n = int(sr * 0.14)
        t = np.linspace(0, 1, n)
        tone = _pitch_sweep(420 - 220 * t, sr)
        growl = bandpass(white_noise(n, rng), sr, 250, 2000) * 0.6
        env = linear_envelope(n, int(sr * 0.004), int(sr * 0.09))
        return (tone * 0.55 + growl) * env

    gap = np.zeros(int(sr * 0.09))
    return np.concatenate([burst(), gap, burst()]) * 1.2


def _shot_bird_chirp(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.22)
    t = np.linspace(0, 1, n)
    freq = 2600 + 1400 * np.sin(2 * np.pi * 3.5 * t)
    tone = _pitch_sweep(freq, sr)
    env = linear_envelope(n, int(sr * 0.01), int(sr * 0.14))
    return tone * env


def _shot_wolf_howl(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 1.8)
    t = np.linspace(0, 1, n)
    freq = 280 + 220 * np.sin(np.pi * t)  # slow rise then fall
    vibrato = 1 + 0.04 * np.sin(2 * np.pi * 5.5 * t)
    tone = _pitch_sweep(freq, sr) * vibrato
    breath = bandpass(white_noise(n, rng), sr, 200, 900) * 0.12
    env = linear_envelope(n, int(sr * 0.35), int(sr * 0.7))
    return (tone + breath) * env


def _shot_cat_meow(sr: int, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * 0.45)
    t = np.linspace(0, 1, n)
    freq = 550 + 380 * np.sin(np.pi * t)  # glide up then down
    tone = _pitch_sweep(freq, sr)
    env = linear_envelope(n, int(sr * 0.05), int(sr * 0.28))
    return tone * env


_ONE_SHOT_KEYWORDS: list[tuple[tuple[str, ...], "callable"]] = [
    (("door", "creak", "hinge"), _shot_door),
    (("dog", "bark", "woof"), _shot_dog_bark),
    (("bird", "chirp", "tweet"), _shot_bird_chirp),
    (("wolf", "howl"), _shot_wolf_howl),
    (("cat", "meow", "yowl"), _shot_cat_meow),
    (("footstep", "step", "walk"), _shot_footstep),
    (("wind", "gust", "breeze"), _shot_wind_gust),
    (("glass", "shatter", "break"), _shot_glass),
    (("bell", "chime", "ring"), _shot_bell),
    (("thud", "impact", "drop", "knock"), _shot_thud),
]


# ---------------------------------------------------------------------------
# Ambience variants of the discrete-event sounds above (bell, dog, wolf, cat).
#
# Module 7's LLM often tags a repeating/ongoing sound ("a bell ringing frantically",
# "a dog barking somewhere in the distance") as an AMBIENT cue rather than a one-shot —
# that's a reasonable classification, but _AMBIENCE_KEYWORDS had no entries for these at
# all, so they silently fell through to _amb_default (plain band-passed white noise —
# audibly just hiss/static, not a recognizable bell or animal). Reusing the one-shot
# generators as scattered discrete hits over a light noise floor keeps them recognizable
# in ambient form too, instead of only when the LLM happens to pick "one-shot".
# ---------------------------------------------------------------------------

def _scatter_shots(
    n: int, sr: int, rng: np.random.Generator, shot_fn, count_range: tuple[int, int], floor_gain: float = 0.02,
) -> np.ndarray:
    out = np.zeros(n)
    floor = bandpass(white_noise(n, rng), sr, 150, 2000) * floor_gain
    count = int(rng.integers(count_range[0], count_range[1] + 1))
    for _ in range(count):
        shot = shot_fn(sr, rng) * rng.uniform(0.4, 0.8)
        if len(shot) >= n:
            continue
        start = int(rng.integers(0, n - len(shot)))
        out[start : start + len(shot)] += shot
    return out + floor


def _amb_bell(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    return _scatter_shots(n, sr, rng, _shot_bell, (2, 4))


def _amb_dog(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    return _scatter_shots(n, sr, rng, _shot_dog_bark, (2, 5))


def _amb_wolf(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    return _scatter_shots(n, sr, rng, _shot_wolf_howl, (1, 2))


def _amb_cat(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    return _scatter_shots(n, sr, rng, _shot_cat_meow, (2, 4))


# Inserted ahead of the generic "bird"/"creak" groups so a specific match (a dog, a
# wolf, a bell) wins over a broader one.
_AMBIENCE_KEYWORDS[:0] = [
    (("bell", "chime", "clock tower"), _amb_bell),
    (("dog", "bark", "woof"), _amb_dog),
    (("wolf", "howl"), _amb_wolf),
    (("cat", "meow", "yowl"), _amb_cat),
]


def generate_one_shot(prompt: str, seed: int | None = None) -> AudioSegment:
    rng = np.random.default_rng(seed)
    prompt_l = prompt.lower()
    generators = _matched_generators(prompt_l, _ONE_SHOT_KEYWORDS, _shot_default)
    clips = [gen(SAMPLE_RATE, rng) for gen in generators]
    if len(clips) == 1:
        samples = clips[0]
    else:
        # Layer distinct sounds named in the same cue (e.g. "dog barking, answered by a
        # wolf") back-to-back with a short gap instead of overlapping — overlapping two
        # sharp transients on top of each other tends to just read as one louder noise,
        # not as two recognizably different sounds.
        gap = np.zeros(int(SAMPLE_RATE * 0.12))
        parts = []
        for i, clip in enumerate(clips):
            if i > 0:
                parts.append(gap)
            parts.append(clip)
        samples = np.concatenate(parts)
    return to_segment(samples * 0.7)
