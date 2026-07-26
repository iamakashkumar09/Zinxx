"""Module 11 — Quality/Consistency Review.

Public API: process(story) -> QAReport

Input: the fully-populated Story from Module 9 (audio_production) — every Line has
emotion_scores/performance_direction/duration_ms, every SoundCue has position_ms. Output:
a QAReport (list of QAIssue + a 0-100 consistency_score). Advisory only — the caller
(app.py) must never let this block Module 10's render.
"""

from modules.module11_qa_consistency.reviewer import review_story
from modules.module11_qa_consistency.schemas import QAIssue, QAReport


def process(story) -> QAReport:
    return review_story(story)
