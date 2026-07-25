"""
Module 3 — Narrative Reconstruction Engine
prompts.py

Pure string-building functions. No side effects, no LLM calls — keep this file
easy to unit test by just printing the output and eyeballing it.

Field-name reference: all graph access uses Module 2's canonical field names:
  Node  -> .id, .label, .type (NodeType enum), .attributes, .is_recurring_symbol
  Edge  -> .from_id, .to_id, .type (EdgeType enum)
  Graph -> .dream_id, .user_id, .version, .nodes, .edges
"""

from __future__ import annotations

from .schemas import DreamGraph, ConversationTurn, ReconstructionConfig, RippleContext
from .config import DEFAULT_CONTEXT


BASE_PERSONA = (
    "You are the Narrative Reconstruction Engine inside a dream-to-audio-drama "
    "pipeline. You receive a structured Dream Graph (characters, locations, "
    "objects/totems, emotions, events, transitions) plus a short window of recent "
    "conversation. Each event node's attributes include a 'summary' field — this is "
    "the ACTUAL concrete content (dialogue said, sounds heard) from the original dream "
    "as first described. Your job is to reconstruct the dream as a sequence of narrative "
    "beats that fills gaps in the graph while PRESERVING dream logic — do not "
    "'fix' surreal or illogical elements into realism. Flag every invented detail "
    "as a gap-fill with a confidence score instead of presenting it as fact."
)

DREAM_LOGIC_RULES = (
    "Dream logic rules:\n"
    "- Impossible transitions (a room becomes a forest, a person becomes someone "
    "else) are FEATURES to keep, not contradictions to resolve.\n"
    "- Emotional truth outranks literal consistency. A dream can be spatially "
    "impossible and still be emotionally coherent — preserve that.\n"
    "- Only flag something as a genuine contradiction if it breaks the dream's own "
    "internal emotional logic, not just physical logic.\n"
    "- Stay concrete, not just emotionally 'true'. Every specific sensory detail in an "
    "event's 'summary' (a sound heard, an object, an action, a line actually said) MUST "
    "show up in narrative_text in some recognizable form — do not launder concrete "
    "detail (thunder, a bell, a dog barking, glass breaking) into vague symbolic or "
    "philosophical prose. Preserving dream logic means keeping the dream's own strange "
    "images and events, not replacing them with abstractions about them.\n"
    "- A non-human presence (an animal, a crowd, a force of nature) should act and make "
    "the sounds/noises a summary describes it making. Only give it human-style spoken "
    "dialogue if the summary shows it actually speaking — otherwise represent it through "
    "action and sound in the narrative_text, not invented philosophical quotes.\n"
)

REALISM_RULES = (
    "Resolve gaps toward the most plausible, literal continuity. Treat inconsistencies "
    "as errors to fix rather than dream logic to preserve."
)


def build_system_prompt(config: ReconstructionConfig) -> str:
    parts = [BASE_PERSONA]
    parts.append(DREAM_LOGIC_RULES if config.preserve_dream_logic else REALISM_RULES)

    if config.layer_persona:
        parts.append(f"Layer instruction (from the Dream Layer Engine): {config.layer_persona}")
    if config.lens_persona:
        parts.append(f"Narrative lens instruction: {config.lens_persona}")

    length_hint = {
        "short": "Produce 3-5 narrative beats.",
        "medium": "Produce 5-9 narrative beats.",
        "long": "Produce 9-15 narrative beats.",
    }[config.target_length]
    parts.append(length_hint)

    parts.append(
        "Respond ONLY with JSON matching the provided schema. No prose outside JSON."
    )
    return "\n\n".join(parts)


def _graph_to_prompt_json(graph: DreamGraph) -> dict:
    """Serialises Module 2's DreamGraph into a compact dict for the LLM prompt.

    Field mapping (Module 2 → prompt JSON):
      Node.id         -> "id"
      Node.label      -> "name"   (kept as "name" in the prompt so the LLM reads
                                   naturally — the internal id is still the id)
      Node.type.value -> grouped by type key
      Node.attributes -> "attributes"
      Node.is_recurring_symbol -> included if True ("recurring_symbol": true)
      Edge.from_id    -> "source"
      Edge.to_id      -> "target"
      Edge.type.value -> "relation"
    """
    cap = DEFAULT_CONTEXT.MAX_GRAPH_NODES_PER_TYPE
    by_type: dict[str, list] = {}
    for node in graph.nodes:
        node_type_key = node.type.value  # NodeType enum → string
        entry: dict = {
            "id": node.id,
            "name": node.label,          # Module 2 uses .label; prompt uses "name" for LLM clarity
            "attributes": node.attributes,
        }
        if node.is_recurring_symbol:
            entry["recurring_symbol"] = True
        if node.matched_totem_id:
            entry["matched_totem"] = node.matched_totem_id
        by_type.setdefault(node_type_key, []).append(entry)
    for t in by_type:
        by_type[t] = by_type[t][:cap]

    return {
        "graph_id": graph.dream_id,      # Module 2's dream_id is the graph identifier
        "user_id": graph.user_id,
        "version": graph.version,
        "nodes_by_type": by_type,
        "edges": [
            {
                "source": e.from_id,     # Module 2: from_id
                "target": e.to_id,       # Module 2: to_id
                "relation": e.type.value # Module 2: EdgeType enum → string
            }
            for e in graph.edges
        ],
    }


def _trim_context(turns: list[ConversationTurn]) -> list[dict]:
    trimmed = turns[-DEFAULT_CONTEXT.MAX_CONTEXT_TURNS:]
    return [{"role": t.role, "text": t.text} for t in trimmed]


def build_user_prompt(
    dream_graph: DreamGraph,
    conversation_context: list[ConversationTurn],
    ripple: RippleContext | None = None,
) -> str:
    import json

    payload = {
        "dream_graph": _graph_to_prompt_json(dream_graph),
        "recent_conversation": _trim_context(conversation_context),
    }

    if ripple is not None:
        payload["regeneration_mode"] = True
        payload["changed_node_ids"] = ripple.changed_node_ids
        payload["previous_beats_summary"] = [
            {"beat_id": b.beat_id, "text": b.narrative_text[:200]}
            for b in ripple.previous_output.beats
        ]
        payload["instruction"] = (
            "Only regenerate beats that causally depend on the changed node ids above. "
            "For unaffected beats, copy them through unchanged (same beat_id, same text)."
        )

    return json.dumps(payload, ensure_ascii=False, indent=2)


# JSON schema handed to the LLM for structured-output enforcement.
NARRATIVE_OUTPUT_SCHEMA = {
    "name": "narrative_reconstruction_output",
    "schema": {
        "type": "object",
        "properties": {
            "beats": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "order": {"type": "integer"},
                        "location_ref": {"type": ["string", "null"]},
                        "characters_present": {"type": "array", "items": {"type": "string"}},
                        "narrative_text": {"type": "string"},
                        "dream_logic_elements": {"type": "array", "items": {"type": "string"}},
                        "emotional_tone": {"type": ["string", "null"]},
                        "gap_fills": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "original_gap_description": {"type": "string"},
                                    "fill_content": {"type": "string"},
                                    "confidence": {"type": "number"},
                                },
                                "required": ["original_gap_description", "fill_content", "confidence"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["order", "narrative_text", "characters_present", "location_ref", "dream_logic_elements", "emotional_tone", "gap_fills"],
                    "additionalProperties": False,
                },
            },
            "implied_new_entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "name": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["type", "name", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["beats", "implied_new_entities"],
        "additionalProperties": False,
    },
    "strict": True,
}
