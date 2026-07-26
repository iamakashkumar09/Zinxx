"""Module 10 — Mixing & Timeline Composition.

Public API: process(story, output_dir) -> Path

Input: the Story produced by Module 9 (audio_production). Output: the path to the final
mixed mp3 file. This is the last stage in the runtime pipeline — its output is what
app.py serves back to the frontend.
"""

from pathlib import Path

from modules.module10_mixing_timeline.mixing import mix_story
from shared.models import Story


def process(story: Story, output_dir: Path) -> Path:
    return mix_story(story, output_dir)
