"""Module 8 — Audio Direction Engine.

Job (per Architecture.md): decide *how* each line should sound — emotional delivery
parameters and timing — before any audio is generated. In this build that's emotion
scoring (local HF classifier) + a Groq call producing natural-language delivery
instructions per line (the architecture doc's `gpt-4o-mini-tts` steering equivalent).

Public API: process(story) -> Story

Input: the Story produced by Module 1 (dream_understanding). Output: the same Story with
every Line's emotion_scores and performance_direction filled in — this becomes Module 9's
(audio_production) input.
"""

from modules.module8_audio_direction import emotion_scoring, performance_direction
from shared.models import Story


def process(story: Story) -> Story:
    story = emotion_scoring.score_story(story)
    story = performance_direction.direct_story(story)
    return story
