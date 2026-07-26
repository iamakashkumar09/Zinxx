"""Module 7 — Screenplay Conversion.

Public API: process(narrative_output, graph, title_hint=None) -> Story

Input: Module 3's NarrativeOutput (reconstructed narrative beats) and Module 2's
DreamGraph (authoritative character/location facts). Output: a Story (shared/models.py) —
the same schema Module 1 produces directly in the fast-preview path — ready to feed
straight into Module 8 (audio_direction).

This is what turns the full 1 -> 2 -> 3 pipeline (dream understanding -> graph ->
reconstructed narrative) into something Modules 8-10 can actually voice, instead of
Module 3's output being a dead end that only gets displayed as text.
"""

from modules.module7_screenplay_conversion.converter import convert_to_screenplay
from shared.models import Story


def process(narrative_output, graph, title_hint: str | None = None) -> Story:
    return convert_to_screenplay(narrative_output, graph, title_hint=title_hint)
