"""Part of Module 9 — Audio Production.

Resolves loose sound-cue position hints ("before line 2", "after line 1", from Module 1's
output) into concrete position_ms values within a scene, using the real per-line TTS
durations produced by voice_generation.py. Output feeds Module 10's (mixing_timeline)
mixing.py, which places one-shot cues at these exact millisecond offsets.
"""

import re

from shared.config import LINE_GAP_MS
from shared.models import Scene, Story

_LINE_REF = re.compile(r"line\s*(\d+)", re.IGNORECASE)


def _line_start_offsets(scene: Scene) -> list[int]:
    """Cumulative start time (ms) of each line within the scene, given LINE_GAP_MS gaps."""
    offsets = []
    cursor = 0
    for line in scene.lines:
        offsets.append(cursor)
        cursor += (line.duration_ms or 0) + LINE_GAP_MS
    return offsets

def _scene_length_ms(scene: Scene) -> int:
    offsets = _line_start_offsets(scene)
    if not offsets:
        return 0
    last = scene.lines[-1]
    return offsets[-1] + (last.duration_ms or 0)


def resolve_positions(story: Story) -> Story:
    for scene in story.scenes:
        starts = _line_start_offsets(scene)
        scene_len = _scene_length_ms(scene)
        for cue in scene.sound_cues:
            if cue.type != "one-shot":
                continue
            if cue.position_ms is not None:
                continue
            hint = (cue.position or "").lower()
            match = _LINE_REF.search(hint)
            if not match or not scene.lines:
                cue.position_ms = 0
                continue
            line_num = max(1, min(len(scene.lines), int(match.group(1))))
            line_idx = line_num - 1
            if "after" in hint:
                cue.position_ms = min(
                    scene_len,
                    starts[line_idx] + (scene.lines[line_idx].duration_ms or 0),
                )
            else:  # "before" or unspecified relation defaults to the line's start
                cue.position_ms = starts[line_idx]
    return story
