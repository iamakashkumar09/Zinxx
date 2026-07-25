"""Module 6 — Multi-Lens Narrative Generation.

Public API: process(graph, session_meta, lens_names=None, model_tier="draft") -> DreamLenses

Input: Module 2's DreamGraph. Output: a DreamLenses bundle — one Module 3 NarrativeOutput
per lens (default: all 5 of psychological / thriller / mystery / fantasy / adventure),
generated in parallel.

Each lens is independently a valid Module 3 NarrativeOutput, so any of them can be fed
into Module 7 (screenplay_conversion) exactly like the default narrative — e.g.
`module7.process(lenses.lenses["thriller"], graph)` gets you the audio-ready screenplay
for just that lens.
"""

from modules.module6_multi_lens_generation.lenses import DreamLenses, LENS_PERSONAS, generate_lenses


async def process(graph, session_meta, lens_names=None, model_tier: str = "draft") -> DreamLenses:
    return await generate_lenses(graph, session_meta, lens_names=lens_names, model_tier=model_tier)
