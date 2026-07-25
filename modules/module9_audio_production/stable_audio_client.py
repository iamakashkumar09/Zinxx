"""Part of Module 9 — Audio Production.

Stable Audio 3 Small client — wraps stable-audio-tools to generate AI music and SFX.

Two separate model instances are loaded lazily on first use:
  - stabilityai/stable-audio-3-small-music  → BGM/music beds
  - stabilityai/stable-audio-3-small-sfx    → ambience + one-shot SFX

Device is auto-detected: CUDA if available, otherwise CPU.
Both models are downloaded automatically from Hugging Face on first run (~500 MB each)
and cached in ~/.cache/huggingface/hub/ for subsequent calls.

Raises RuntimeError immediately if stable-audio-tools is not installed or model
loading / inference fails — no silent fallback.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import numpy as np
import torch
from pydub import AudioSegment

from shared.config import STABLE_AUDIO_MUSIC_MODEL, STABLE_AUDIO_SFX_MODEL

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Device selection — auto-detect CUDA, fall to CPU
# ---------------------------------------------------------------------------

def _get_device() -> str:
    if torch.cuda.is_available():
        device = "cuda"
        print(f"[StableAudio] CUDA detected — using GPU ({torch.cuda.get_device_name(0)})")
    else:
        device = "cpu"
        print("[StableAudio] No CUDA detected — using CPU (expect slower generation)")
    return device


DEVICE = _get_device()

# ---------------------------------------------------------------------------
# Lazy model singletons — loaded on first call to avoid slow import-time cost
# ---------------------------------------------------------------------------

_music_model = None
_music_config = None
_sfx_model = None
_sfx_config = None


def _load_music_model():
    global _music_model, _music_config
    if _music_model is not None:
        return _music_model, _music_config
    try:
        from stable_audio_tools import get_pretrained_model
    except ImportError as e:
        raise RuntimeError(
            "stable-audio-tools is not installed. Run: pip install stable-audio-tools"
        ) from e
    print(f"[StableAudio] Loading music model: {STABLE_AUDIO_MUSIC_MODEL} ...")
    _music_model, _music_config = get_pretrained_model(STABLE_AUDIO_MUSIC_MODEL)
    _music_model = _music_model.to(DEVICE)
    _music_model.eval()
    print("[StableAudio] Music model loaded.")
    return _music_model, _music_config


def _load_sfx_model():
    global _sfx_model, _sfx_config
    if _sfx_model is not None:
        return _sfx_model, _sfx_config
    try:
        from stable_audio_tools import get_pretrained_model
    except ImportError as e:
        raise RuntimeError(
            "stable-audio-tools is not installed. Run: pip install stable-audio-tools"
        ) from e
    print(f"[StableAudio] Loading SFX model: {STABLE_AUDIO_SFX_MODEL} ...")
    _sfx_model, _sfx_config = get_pretrained_model(STABLE_AUDIO_SFX_MODEL)
    _sfx_model = _sfx_model.to(DEVICE)
    _sfx_model.eval()
    print("[StableAudio] SFX model loaded.")
    return _sfx_model, _sfx_config


# ---------------------------------------------------------------------------
# Internal generation helper
# ---------------------------------------------------------------------------

def _generate(model, model_config, prompt: str, seconds: float) -> AudioSegment:
    """Run diffusion generation and return a pydub AudioSegment."""
    try:
        from stable_audio_tools.inference.generation import generate_diffusion_cond
    except ImportError as e:
        raise RuntimeError(
            "stable-audio-tools is not installed. Run: pip install stable-audio-tools"
        ) from e

    sample_rate: int = model_config["sample_rate"]
    sample_size: int = model_config.get("sample_size", int(sample_rate * seconds))

    conditioning = [
        {
            "prompt": prompt,
            "seconds_start": 0,
            "seconds_total": seconds,
        }
    ]

    with torch.inference_mode():
        output = generate_diffusion_cond(
            model,
            steps=100,
            cfg_scale=7,
            conditioning=conditioning,
            sample_size=sample_size,
            sigma_min=0.3,
            sigma_max=500,
            sampler_type="dpmpp-3m-sde",
            device=DEVICE,
        )

    # output shape: [batch, channels, samples]  — take first item
    audio_tensor = output[0]  # [channels, samples]

    # Convert to numpy → pydub
    audio_np = audio_tensor.cpu().float().numpy()
    # Mix down to mono if stereo
    if audio_np.ndim > 1 and audio_np.shape[0] > 1:
        audio_np = audio_np.mean(axis=0)
    elif audio_np.ndim > 1:
        audio_np = audio_np[0]

    # Normalise to [-1, 1]
    peak = np.abs(audio_np).max()
    if peak > 1e-9:
        audio_np = audio_np / peak * 0.85

    pcm16 = (audio_np * 32767).astype(np.int16)
    segment = AudioSegment(
        data=pcm16.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=1,
    )
    return segment


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_music(prompt: str, duration_ms: int) -> AudioSegment:
    """Generate a music bed using Stable Audio 3 Small Music.

    Args:
        prompt: A text description of the desired music (e.g. "dark ambient drone, slow").
        duration_ms: Target duration in milliseconds.

    Returns:
        AudioSegment with the generated music, trimmed/padded to duration_ms.

    Raises:
        RuntimeError: If stable-audio-tools is not installed or generation fails.
    """
    if duration_ms <= 0:
        return AudioSegment.silent(duration=0)

    seconds = duration_ms / 1000.0
    model, config = _load_music_model()
    print(f"[StableAudio] Generating music: '{prompt}' ({seconds:.1f}s) ...")
    segment = _generate(model, config, prompt, seconds)
    print(f"[StableAudio] Music generated ({len(segment)}ms).")

    # Trim or pad to exact requested duration
    if len(segment) > duration_ms:
        segment = segment[:duration_ms]
    elif len(segment) < duration_ms:
        segment = segment + AudioSegment.silent(duration=duration_ms - len(segment))
    return segment


def generate_sfx(prompt: str, duration_ms: int) -> AudioSegment:
    """Generate a sound effect using Stable Audio 3 Small SFX.

    Args:
        prompt: A text description of the desired SFX (e.g. "howling wind, distant").
        duration_ms: Target duration in milliseconds. For one-shots, pass 0 and
                     the model will generate a natural-length clip.

    Returns:
        AudioSegment with the generated SFX.

    Raises:
        RuntimeError: If stable-audio-tools is not installed or generation fails.
    """
    seconds = max(duration_ms / 1000.0, 1.0)  # minimum 1s even for one-shots
    model, config = _load_sfx_model()
    print(f"[StableAudio] Generating SFX: '{prompt}' ({seconds:.1f}s) ...")
    segment = _generate(model, config, prompt, seconds)
    print(f"[StableAudio] SFX generated ({len(segment)}ms).")

    if duration_ms > 0 and len(segment) > duration_ms:
        segment = segment[:duration_ms]
    return segment
