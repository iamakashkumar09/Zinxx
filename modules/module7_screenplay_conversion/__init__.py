"""Module 7 — Screenplay Conversion. Folded into Module 1 in this build.

Per Architecture.md: turn the finalized narrative into a structured screenplay JSON
(scenes, dialogue lines tagged by character, SFX cues, music cues, pacing notes) — the
contract between the text pipeline and the audio pipeline.

Current status: Module 1's (dream_understanding) single Groq call already emits this
shape directly (see shared/models.py's Story/Scene/Line/SoundCue schema) as part of its one
JSON response, since there's no separate narrative-reconstruction pass to convert from yet.

If you pick this up: split it out once Module 3 (narrative_reconstruction) exists as its
own step — this module would then take plain reconstructed narrative text and convert it
into the Story JSON schema, rather than doing extraction + reconstruction + conversion in
one prompt.
"""


def process(*args, **kwargs):
    raise NotImplementedError(
        "Module 7 (Screenplay Conversion) is not a separate step in this build — its job "
        "currently happens inside module1_dream_understanding/story_extraction.py, which "
        "emits the Story JSON schema (shared/models.py) directly."
    )
