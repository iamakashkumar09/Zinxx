"""Module 10 — Mixing & Timeline Composition.

Combines Module 9's per-line voice clips + procedurally-synthesized ambience/one-shot cues
into a single mixed audio drama. Ambience "ducking" is a fixed low-gain underlay rather than
true sidechain compression — simple and good enough for a short demo track. No per-layer
reverb (Architecture.md's Module 4 dream layers aren't implemented in this build).

Public API: process(story, output_dir) -> Path

Input: the Story produced by Module 9 (audio_production) — every Line has audio_path, every
one-shot SoundCue has position_ms. Output: the path to the final mixed mp3.
"""

import uuid
from pathlib import Path

from pydub import AudioSegment, effects

from modules.module9_audio_production.sfx_synth import generate_ambience, generate_one_shot
from shared.config import AMBIENCE_GAIN_DB, LINE_GAP_MS, ONE_SHOT_GAIN_DB, SCENE_CROSSFADE_MS
from shared.models import Story

MIN_SCENE_MS = 2000


def _build_dialogue_track(scene) -> AudioSegment:
    if not scene.lines:
        return AudioSegment.silent(duration=MIN_SCENE_MS)

    track = AudioSegment.silent(duration=0)
    gap = AudioSegment.silent(duration=LINE_GAP_MS)
    for line in scene.lines:
        clip = AudioSegment.from_file(line.audio_path, format="mp3")
        track += clip + gap
    return track


def _build_scene_track(scene) -> AudioSegment:
    dialogue = _build_dialogue_track(scene)
    scene_track = dialogue

    for cue in scene.sound_cues:
        if cue.type != "ambient":
            continue
        bed = generate_ambience(cue.prompt, duration_ms=len(dialogue)).apply_gain(AMBIENCE_GAIN_DB)
        scene_track = scene_track.overlay(bed, position=0)

    for cue in scene.sound_cues:
        if cue.type != "one-shot":
            continue
        position = max(0, min(cue.position_ms or 0, len(scene_track)))
        shot = generate_one_shot(cue.prompt).apply_gain(ONE_SHOT_GAIN_DB)
        scene_track = scene_track.overlay(shot, position=position)

    return scene_track


def mix_story(story: Story, output_dir: Path) -> Path:
    scene_tracks = [_build_scene_track(scene) for scene in story.scenes]
    if not scene_tracks:
        raise ValueError("Story has no scenes to mix.")

    final = scene_tracks[0]
    for next_track in scene_tracks[1:]:
        crossfade = min(SCENE_CROSSFADE_MS, len(final), len(next_track))
        final = final.append(next_track, crossfade=max(0, crossfade))

    final = effects.normalize(final)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"dream_{uuid.uuid4().hex[:10]}.mp3"
    final.export(out_path, format="mp3", bitrate="192k")
    return out_path
