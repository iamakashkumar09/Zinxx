"""Shared data contract — the Story object that flows between all 4 modules.

Module 1 (story_intelligence) produces a Story.
Module 2 (audio_direction) fills in Line.emotion_scores + Line.performance_direction.
Module 3 (audio_production) fills in Line.audio_path/duration_ms + SoundCue.position_ms.
Module 4 (mix_delivery) consumes the fully-populated Story to render the final audio.

Do not change field names/types without syncing with all 4 module owners — this file is
the integration contract.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Character(BaseModel):
    id: str
    name: str
    role: str


class SoundCue(BaseModel):
    type: Literal["ambient", "one-shot"]
    prompt: str
    position: Optional[str] = None
    position_ms: Optional[int] = None


class Line(BaseModel):
    speaker: str
    text: str
    emotion_scores: Optional[dict[str, float]] = None
    performance_direction: Optional[str] = None
    audio_path: Optional[str] = None
    duration_ms: Optional[int] = None


class Scene(BaseModel):
    id: int
    setting: str
    emotional_tone: str
    lines: list[Line]
    sound_cues: list[SoundCue] = Field(default_factory=list)


class Story(BaseModel):
    title: str
    characters: list[Character]
    scenes: list[Scene]


class StoryRequest(BaseModel):
    text: str


class AudioRequest(BaseModel):
    story: Story


class AudioResponse(BaseModel):
    audio_url: str
    story: Story
