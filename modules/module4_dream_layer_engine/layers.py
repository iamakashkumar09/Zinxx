"""Module 4 — Dream Layer Engine (Inception-style).

Job (per Architecture.md): organize the reconstructed narrative across layers (conscious
dream / subconscious memory / hidden fear / symbolic truth) and let recurring totems
recur meaningfully across layers.

Not a separate model — an orchestration pattern: runs Module 3's engine multiple times
against the SAME Dream Graph, each with a different `layer_persona` system-prompt
instruction, in parallel (each layer is an independent, unrelated LLM call, so there's no
reason to serialize them). Recurring totems (nodes Module 2's totems.py already flagged as
`is_recurring_symbol` via embedding similarity across past dreams) are cross-referenced
across the generated layers via Module 3's provenance_map, so you can show "the red door
shows up in the conscious dream AND the hidden fear layer."
"""

import asyncio
from dataclasses import dataclass, field

from modules.module2_dream_graph.models import DreamGraph
from modules.module3_narrative_reconstruction import (
    NarrativeOutput,
    NarrativeReconstructionEngine,
    ReconstructionConfig,
    SessionMeta,
)

LAYER_PERSONAS = {
    "conscious_dream": (
        "Write the CONSCIOUS DREAM layer: the dream exactly as experienced, moment to "
        "moment, staying close to the literal events and imagery in the graph. This is "
        "the surface narrative — what the dreamer would say happened if asked to retell it."
    ),
    "subconscious_memory": (
        "Write the SUBCONSCIOUS MEMORY layer: reinterpret the same graph as a distorted "
        "echo of a real memory. Ground the same characters/locations/events in something "
        "that plausibly really happened, filtered and warped by time and emotion."
    ),
    "hidden_fear": (
        "Write the HIDDEN FEAR layer: reinterpret the same graph as an anxiety made "
        "literal — what is the dreamer actually afraid of, and how does each element "
        "(character, location, object) symbolize that fear?"
    ),
    "symbolic_truth": (
        "Write the SYMBOLIC TRUTH layer: reinterpret the same graph as pure symbol — "
        "treat every character, location, and object as a metaphor and state plainly what "
        "each one represents, narrated as a revealed meaning rather than a scene."
    ),
}


@dataclass
class DreamLayers:
    layers: dict[str, NarrativeOutput] = field(default_factory=dict)
    # totem/character/location node id -> which layer names actually referenced it
    totem_cross_references: dict[str, list[str]] = field(default_factory=dict)
    # layer name -> error message, for any layer whose LLM call failed — a bad layer
    # should never take down the others, since they're fully independent calls
    errors: dict[str, str] = field(default_factory=dict)


def _cross_reference_totems(graph: DreamGraph, layers: dict[str, NarrativeOutput]) -> dict[str, list[str]]:
    recurring_ids = {n.id for n in graph.nodes if n.is_recurring_symbol}
    if not recurring_ids:
        return {}
    refs: dict[str, list[str]] = {nid: [] for nid in recurring_ids}
    for layer_name, output in layers.items():
        referenced_in_layer: set[str] = set()
        for node_ids in output.provenance_map.values():
            referenced_in_layer.update(node_ids)
        for nid in recurring_ids:
            if nid in referenced_in_layer:
                refs[nid].append(layer_name)
    return {nid: names for nid, names in refs.items() if names}


async def generate_layers(
    graph: DreamGraph,
    session_meta: SessionMeta,
    layer_names: list[str] | None = None,
    model_tier: str = "draft",
) -> DreamLayers:
    names = layer_names or list(LAYER_PERSONAS.keys())
    unknown = [n for n in names if n not in LAYER_PERSONAS]
    if unknown:
        raise ValueError(f"Unknown dream layer(s): {unknown}. Known layers: {list(LAYER_PERSONAS)}")

    async def _run_layer(name: str) -> NarrativeOutput:
        config = ReconstructionConfig(
            model_tier=model_tier, layer_persona=LAYER_PERSONAS[name], preserve_dream_logic=True
        )
        request = NarrativeReconstructionEngine.input_from_graph(
            graph=graph, session_meta=session_meta, config=config
        )
        # .reconstruct() is a synchronous/blocking network call — push it off the event
        # loop thread so the layers genuinely run concurrently, not one after another.
        return await asyncio.to_thread(NarrativeReconstructionEngine().reconstruct, request)

    results = await asyncio.gather(*[_run_layer(n) for n in names], return_exceptions=True)

    layers: dict[str, NarrativeOutput] = {}
    errors: dict[str, str] = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            errors[name] = str(result)
        else:
            layers[name] = result

    return DreamLayers(
        layers=layers,
        totem_cross_references=_cross_reference_totems(graph, layers),
        errors=errors,
    )
