"""Module 4 — Dream Layer Engine (Inception-style).

Public API: process(graph, session_meta, layer_names=None, model_tier="draft") -> DreamLayers

Input: Module 2's DreamGraph. Output: a DreamLayers bundle — one Module 3 NarrativeOutput
per layer (default: all 4 of conscious_dream / subconscious_memory / hidden_fear /
symbolic_truth), generated in parallel, plus a cross-reference of which recurring totems
appear in which layers.

Each layer is independently a valid Module 3 NarrativeOutput, so any of them can be fed
into Module 7 (screenplay_conversion) exactly like the default single-layer narrative —
e.g. `module7.process(layers.layers["hidden_fear"], graph)` gets you the audio-ready
screenplay for just that layer.
"""

from modules.module4_dream_layer_engine.layers import DreamLayers, LAYER_PERSONAS, generate_layers


async def process(graph, session_meta, layer_names=None, model_tier: str = "draft") -> DreamLayers:
    return await generate_layers(graph, session_meta, layer_names=layer_names, model_tier=model_tier)
