"""Module 5 — Interactive Ripple Regeneration.

Public API:
    apply_edit(dream_id, node_id, new_label=None, new_attributes=None) -> (DreamGraph, changed_node_ids)
    find_affected_beats(previous_narrative, changed_node_ids) -> list[beat_id]   (free, no LLM call)
    process(dream_id, user_id, session_id, node_id, previous_narrative, ...) -> RippleResult

Input: a dream_id with an already-persisted graph (from /api/dream), the node to edit, and
the NarrativeOutput that graph previously produced. Output: a new graph version, a new
NarrativeOutput (only the causally-affected beats actually regenerated — the rest copied
through unchanged by Module 3's own ripple-aware prompt), and which beats were touched.

Feed RippleResult.narrative straight into Module 7 (screenplay_conversion) with
RippleResult.graph to get an updated, audio-ready Story.
"""

from modules.module5_ripple_regeneration.ripple import (
    RippleResult,
    apply_edit,
    find_affected_beats,
    regenerate,
)


async def process(
    dream_id: str,
    user_id: str,
    session_id: str,
    node_id: str,
    previous_narrative,
    new_label: str | None = None,
    new_attributes: dict[str, str] | None = None,
    model_tier: str = "draft",
) -> RippleResult:
    return await regenerate(
        dream_id=dream_id,
        user_id=user_id,
        session_id=session_id,
        node_id=node_id,
        previous_narrative=previous_narrative,
        new_label=new_label,
        new_attributes=new_attributes,
        model_tier=model_tier,
    )
