"""
Module 3 — Narrative Reconstruction Engine
postprocess.py

Pure Python, no LLM calls. This is what makes ripple regeneration (Module 5) cheap:
these functions can re-run on cached beats without spending money.

All graph node access uses Module 2's canonical field name: Node.id (not node_id).
"""

from __future__ import annotations

from .schemas import DreamGraph, NarrativeBeat, GraphUpdate


def build_provenance_map(beats: list[NarrativeBeat]) -> dict[str, list[str]]:
    """Maps beat_id -> list of graph node ids it references (location + characters).
    Used by Module 5 to know which beats depend on a changed node, and by Module 11
    for consistency QA."""
    provenance: dict[str, list[str]] = {}
    for beat in beats:
        refs = list(beat.characters_present)
        if beat.location_ref:
            refs.append(beat.location_ref)
        provenance[beat.beat_id] = refs
    return provenance


def detect_contradictions(beats: list[NarrativeBeat], dream_graph: DreamGraph) -> list[str]:
    """Cross-checks beat references against the graph. Never raises — appends
    human-readable warnings instead, so a bad LLM output never crashes the pipeline.

    Uses Module 2's Node.id field (not the old Module 3 alias .node_id).
    """
    warnings: list[str] = []
    # Module 2's Node uses .id as the primary key, not .node_id
    known_ids = {n.id for n in dream_graph.nodes}

    for beat in beats:
        for char_id in beat.characters_present:
            if char_id not in known_ids:
                warnings.append(
                    f"Beat {beat.beat_id}: character '{char_id}' not found in Dream Graph "
                    f"(likely a new entity the LLM invented — check graph_updates)."
                )
        if beat.location_ref and beat.location_ref not in known_ids:
            warnings.append(
                f"Beat {beat.beat_id}: location '{beat.location_ref}' not found in Dream Graph."
            )
        for gap_fill in beat.gap_fills:
            if gap_fill.confidence < 0.3:
                warnings.append(
                    f"Beat {beat.beat_id}: low-confidence gap fill "
                    f"({gap_fill.confidence:.2f}) — consider asking the user to confirm: "
                    f"'{gap_fill.fill_content}'"
                )
    return warnings


def extract_graph_updates(implied_new_entities: list[dict]) -> list[GraphUpdate]:
    """Turns LLM-reported new entities into GraphUpdate objects for Module 2 to merge.
    Module 3 never writes to the graph store directly — it only proposes updates."""
    updates: list[GraphUpdate] = []
    for entity in implied_new_entities:
        updates.append(
            GraphUpdate(
                kind="node",
                payload={
                    "type": entity.get("type", "object"),
                    "name": entity.get("name", "unnamed"),
                    "attributes": {"origin": "inferred_by_module_3", "reason": entity.get("reason", "")},
                },
            )
        )
    return updates
