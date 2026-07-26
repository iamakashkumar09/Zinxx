"""Module 1 — Dream Understanding & Conversational Recovery.

Job (per Architecture.md): parse the raw dream text and extract entities/emotions/scene
structure. In this build, a single Groq call also does the work of Module 3 (Narrative
Reconstruction — filling gaps while preserving dream logic) and Module 7 (Screenplay
Conversion — emitting the final structured scene/dialogue/cue JSON) in one pass, since
this build has no conversational follow-up loop and no persistent Dream Graph (see
module2_dream_graph/ and module3_narrative_reconstruction/ for where those would plug in
if built out).

Public API:
    process(raw_text) -> Story
    transcribe(file_bytes, filename) -> str   (optional voice input, see transcription.py)

Input: the user's raw dream/memory text (typed, or transcribed from speech via
transcribe()). Output: a fully structured Story (title, characters, scenes, lines, sound
cues) — this becomes Module 8's (audio_direction) input.
"""

from modules.module1_dream_understanding.story_extraction import extract_story
from modules.module1_dream_understanding.transcription import transcribe_audio
from shared.models import Story


def process(raw_text: str) -> Story:
    return extract_story(raw_text)


def transcribe(file_bytes: bytes, filename: str) -> str:
    return transcribe_audio(file_bytes, filename)
