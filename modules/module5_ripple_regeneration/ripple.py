"""Module 5 — Interactive Ripple Regeneration.

Job (per Architecture.md): when a user edits a decision or recalls a new detail mid-story,
regenerate everything downstream without breaking consistency, and without re-running the
whole story (keeps the OpenAI bill sane when users experiment with edits).

How it actually works here, built entirely on hooks Module 3 already exposes:
  1. Load the current DreamGraph (Module 2, versioned by dream_id+version), apply the
     edit to the target node, persist it as a NEW version — the old version stays intact.
  2. Use Module 3's `provenance_map` (beat_id -> [node_ids it references]) to find which
     narrative beats causally depend on the changed node — this is pure Python, no LLM
     call, and it's the "diff the graph, find affected nodes" step from the architecture
     doc, minus needing our own graph-diffing logic since Module 3 already tracked
     per-beat provenance when it first generated the narrative.
  3. Call Module 3's engine again with `ReconstructionInput.ripple` populated
     (`RippleContext(previous_output=..., changed_node_ids=...)`). Module 3's own prompt
     (see prompts.py's `build_user_prompt`) already instructs the model to regenerate only
     the affected beats and copy the rest through unchanged — that logic lives in Module 3
     by design, not duplicated here.
  4. Re-run Module 7 (screenplay conversion) on the resulting narrative. Module 7 is a
     single fast LLM call regardless of story length, so there's no need for a separate
     "partial screenplay" mechanism — the savings from ripple regeneration come from
     Module 3 not re-writing untouched beats, which is the expensive/slow part.
"""

import asyncio
from dataclasses import dataclass, field

from modules.module2_dream_graph.db import load_graph, persist_graph
from modules.module2_dream_graph.models import DreamGraph
from modules.module3_narrative_reconstruction import (
    NarrativeOutput,
    NarrativeReconstructionEngine,
    ReconstructionConfig,
    SessionMeta,
)
from modules.module3_narrative_reconstruction.schemas import RippleContext


@dataclass
class RippleResult:
    graph: DreamGraph
    narrative: NarrativeOutput
    changed_node_ids: list[str]
    affected_beat_ids: list[str]  # beats Module 3 was told to actually regenerate


def find_affected_beats(
    previous_narrative: NarrativeOutput,
    changed_node_ids: list[str],
    changed_node_aliases: list[str] | None = None,
) -> list[str]:
    """Pure Python, no LLM call — this is what makes even *checking* the blast radius
    of an edit free before you commit to spending money regenerating it.

    Matches on node id AND on `changed_node_aliases` (pass the node's label/name here).
    Necessary because Module 3's LLM doesn't always put node ids in a beat's
    `characters_present`/`location_ref` — it sometimes echoes back the character/location
    *name* instead (the prompt shows both, and the id is meant to be canonical, but model
    output isn't perfectly reliable about which one it copies). Matching only on id would
    silently mark a renamed character's own beats as unaffected.
    """
    changed = set(changed_node_ids) | set(changed_node_aliases or [])
    return [
        beat_id
        for beat_id, node_ids in previous_narrative.provenance_map.items()
        if changed & set(node_ids)
    ]


async def apply_edit(
    dream_id: str,
    node_id: str,
    new_label: str | None = None,
    new_attributes: dict[str, str] | None = None,
) -> tuple[DreamGraph, list[str], str]:
    """Loads the latest persisted graph, edits one node, persists the result as a new
    version. The old version is untouched — Module 2's db.py keys rows by (dream_id,
    version), so this is purely additive. Returns the node's OLD label too — the previous
    narrative was generated against that name, so find_affected_beats needs it to catch
    beats that reference the character/location by name instead of id."""
    current = await load_graph(dream_id)
    if current is None:
        raise ValueError(f"No graph found for dream_id={dream_id!r}. Run /api/dream first.")

    target = current.node(node_id)
    if target is None:
        raise ValueError(f"Node {node_id!r} not found in graph for dream {dream_id!r}.")
    if new_label is None and not new_attributes:
        raise ValueError("Edit must change something — pass new_label and/or new_attributes.")

    old_label = target.label
    updated_node = target.model_copy(
        update={
            "label": new_label if new_label is not None else target.label,
            "attributes": {**target.attributes, **(new_attributes or {})},
        }
    )
    new_nodes = [updated_node if n.id == node_id else n for n in current.nodes]

    new_graph = DreamGraph(
        dream_id=current.dream_id,
        user_id=current.user_id,
        version=current.version + 1,
        nodes=new_nodes,
        edges=current.edges,
    )
    await persist_graph(new_graph)
    return new_graph, [node_id], old_label


async def regenerate(
    dream_id: str,
    user_id: str,
    session_id: str,
    node_id: str,
    previous_narrative: NarrativeOutput,
    new_label: str | None = None,
    new_attributes: dict[str, str] | None = None,
    model_tier: str = "draft",
) -> RippleResult:
    new_graph, changed_node_ids, old_label = await apply_edit(
        dream_id=dream_id, node_id=node_id, new_label=new_label, new_attributes=new_attributes
    )
    affected_beat_ids = find_affected_beats(previous_narrative, changed_node_ids, changed_node_aliases=[old_label])

    config = ReconstructionConfig(model_tier=model_tier, preserve_dream_logic=True)
    request = NarrativeReconstructionEngine.input_from_graph(
        graph=new_graph,
        session_meta=SessionMeta(dream_id=dream_id, user_id=user_id, session_id=session_id),
        config=config,
    )
    request.ripple = RippleContext(previous_output=previous_narrative, changed_node_ids=changed_node_ids)

    new_narrative = await asyncio.to_thread(NarrativeReconstructionEngine().reconstruct, request)

    return RippleResult(
        graph=new_graph,
        narrative=new_narrative,
        changed_node_ids=changed_node_ids,
        affected_beat_ids=affected_beat_ids,
    )
