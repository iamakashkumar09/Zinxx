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


_FALLBACK_STAGGER_MS = 450
_SAME_ANCHOR_STAGGER_MS = 380


def resolve_positions(story: Story) -> Story:
    for scene in story.scenes:
        starts = _line_start_offsets(scene)
        scene_len = _scene_length_ms(scene)
        fallback_count = 0
        anchor_counts: dict[tuple[int, str], int] = {}
        for cue in scene.sound_cues:
            if cue.type != "one-shot":
                continue
            if cue.position_ms is not None:
                continue
            hint = (cue.position or "").lower()
            match = _LINE_REF.search(hint)
            if not match or not scene.lines:
                # No line to anchor to (often a lineless action/sound-only beat with
                # several cues) — stagger instead of stacking every cue at 0ms at once.
                cue.position_ms = fallback_count * _FALLBACK_STAGGER_MS
                fallback_count += 1
                continue
            line_num = max(1, min(len(scene.lines), int(match.group(1))))
            line_idx = line_num - 1
            relation = "after" if "after" in hint else "before"
            base = (
                min(scene_len, starts[line_idx] + (scene.lines[line_idx].duration_ms or 0))
                if relation == "after"
                else starts[line_idx]
            )
            # Multiple cues commonly share the same hint verbatim (e.g. four different
            # one-shots all saying "before line 1") — without staggering, they land on the
            # exact same millisecond and get mixed as one simultaneous pile-up, burying
            # individually-distinct sounds (a cat yowl, glass breaking) into indistinct noise.
            anchor = (line_idx, relation)
            offset = anchor_counts.get(anchor, 0) * _SAME_ANCHOR_STAGGER_MS
            anchor_counts[anchor] = anchor_counts.get(anchor, 0) + 1
            cue.position_ms = min(scene_len, base + offset) if scene_len else base + offset
    return story
