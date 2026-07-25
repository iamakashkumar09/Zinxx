"""Module 11 — Quality/Consistency Review. NOT IMPLEMENTED in this build.

Per Architecture.md: one cheap LLM pass over the finished screenplay + generated-audio
metadata (durations, cue list) before final render, to catch things like a character
voice/emotion contradiction or a "door opened" line with no door SFX.

Why skipped: lowest priority per the architecture doc's own build order (step 6, after the
core pipeline works) — text-only reasoning task, nearly free to add once Modules 1-10 are
solid.

If you pick this up: add it as an optional pass in app.py between Module 9
(audio_production) and Module 10 (mixing_timeline) — feed it the Story with durations/cues
already populated, have it flag (not auto-fix) issues for the mixing step or UI to surface.
"""


def process(*args, **kwargs):
    raise NotImplementedError(
        "Module 11 (QA/Consistency Review) is not implemented in this build. "
        "Lowest priority per Architecture.md's own build order."
    )
