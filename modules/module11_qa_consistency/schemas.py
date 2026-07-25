"""Module 11 — Quality/Consistency Review. Pure data shapes, no logic."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QAIssue:
    scene_id: int
    category: str  # "voice_emotion_contradiction" | "missing_sfx" | "other"
    severity: str  # "low" | "medium" | "high"
    description: str
    line_index: Optional[int] = None


@dataclass
class QAReport:
    issues: list[QAIssue] = field(default_factory=list)
    consistency_score: int = 100  # 0-100, 100 = nothing flagged
    model: str = ""
