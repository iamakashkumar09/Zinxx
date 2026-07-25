"""Shared data contract — the Story object that flows between all modules.

Module 1 (dream_understanding) produces a Story.
Module 2 (dream_graph) consumes Story and produces a DreamGraph (in module2_dream_graph.models).
Module 3 (narrative_reconstruction) consumes DreamGraph and produces NarrativeOutput.
Module 8 (audio_direction) fills in Line.emotion_scores + Line.performance_direction.
Module 9 (audio_production) fills in Line.audio_path/duration_ms + SoundCue.position_ms.
Module 10 (mix_delivery) consumes the fully-populated Story to render the final audio.

Do not change field names/types without syncing with all module owners — this file is
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


# ---------------------------------------------------------------------------
# Module 1 → API request/response (existing)
# ---------------------------------------------------------------------------

class StoryRequest(BaseModel):
    text: str


class AudioRequest(BaseModel):
    story: Story


class AudioResponse(BaseModel):
    audio_url: str
    story: Story


# ---------------------------------------------------------------------------
# Module 1 → 2 → 3 pipeline request/response (new)
# ---------------------------------------------------------------------------

class DreamRequest(BaseModel):
    """Request body for the /api/dream endpoint.

    text:       The raw dream description the user typed or spoke.
    user_id:    Stable identifier for the user (used for totem memory across sessions).
    session_id: Identifier for this specific Q&A session (can be a new uuid per run).
    model_tier: "draft" uses gpt-5.4-mini (cheap, for dev); "final" uses gpt-5.4 (demo quality).
    """
    text: str
    user_id: str = "anonymous"
    session_id: Optional[str] = None
    model_tier: Literal["draft", "final"] = "draft"


class NarrativeBeatResponse(BaseModel):
    """A single narrative beat in the Module 3 output, serialised for the API."""
    beat_id: str
    order: int
    location_ref: Optional[str] = None
    characters_present: list[str] = Field(default_factory=list)
    narrative_text: str
    dream_logic_elements: list[str] = Field(default_factory=list)
    emotional_tone: Optional[str] = None
    gap_fills: list[dict] = Field(default_factory=list)


class DreamResponse(BaseModel):
    """Response from the /api/dream endpoint — full Module 1→2→3→7 pipeline output."""
    dream_id: str
    story: Story                                   # Module 7 output — built FROM narrative_beats, not raw Module 1
    narrative_beats: list[NarrativeBeatResponse]    # Module 3 output
    warnings: list[str] = Field(default_factory=list)
    graph_updates: list[dict] = Field(default_factory=list)
    generation_metadata: Optional[dict] = None


# ---------------------------------------------------------------------------
# Module 4 — Dream Layer Engine
# ---------------------------------------------------------------------------

class DreamLayersRequest(BaseModel):
    text: str
    user_id: str = "anonymous"
    session_id: Optional[str] = None
    layer_names: Optional[list[str]] = None  # defaults to all 4 layers if omitted
    model_tier: Literal["draft", "final"] = "draft"


class DreamLayersResponse(BaseModel):
    dream_id: str
    layers: dict[str, list[NarrativeBeatResponse]]
    totem_cross_references: dict[str, list[str]] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Module 6 — Multi-Lens Narrative Generation
# ---------------------------------------------------------------------------

class DreamLensesRequest(BaseModel):
    text: str
    user_id: str = "anonymous"
    session_id: Optional[str] = None
    lens_names: Optional[list[str]] = None  # defaults to all 5 lenses if omitted
    model_tier: Literal["draft", "final"] = "draft"


class DreamLensesResponse(BaseModel):
    dream_id: str
    lenses: dict[str, list[NarrativeBeatResponse]]
    errors: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Module 5 — Interactive Ripple Regeneration
# ---------------------------------------------------------------------------

class DreamEditRequest(BaseModel):
    """previous_narrative_beats is the client's own copy of the narrative_beats it got
    back from /api/dream — the server doesn't persist NarrativeOutput, so ripple
    regeneration's provenance diffing is recomputed from what the client already has,
    the same stateless pattern /api/audio uses for Story."""
    dream_id: str
    user_id: str
    session_id: str
    node_id: str
    new_label: Optional[str] = None
    new_attributes: dict[str, str] = Field(default_factory=dict)
    previous_narrative_beats: list[NarrativeBeatResponse]
    model_tier: Literal["draft", "final"] = "draft"


class DreamEditResponse(BaseModel):
    dream_id: str
    story: Story
    narrative_beats: list[NarrativeBeatResponse]
    changed_node_ids: list[str]
    affected_beat_ids: list[str]  # beats that were actually regenerated, not copied through
