"""Module 6 — Multi-Lens Narrative Generation.

Job (per Architecture.md): the same dream, told through different genre lenses
(psychological / thriller / mystery / fantasy / adventure).

Structurally the same orchestration pattern as Module 4 (Dream Layer Engine): runs Module
3's engine multiple times against the SAME Dream Graph, one call per lens, each with a
different `lens_persona` system-prompt instruction, in parallel — independent calls, no
reason to serialize them.
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

LENS_PERSONAS = {
    "psychological": (
        "Tell this dream through a PSYCHOLOGICAL lens: foreground the dreamer's internal "
        "emotional state, unspoken motivations, and interpersonal tension. Dialogue and "
        "narration should read like a character study."
    ),
    "thriller": (
        "Tell this dream through a THRILLER lens: foreground tension, urgency, and stakes. "
        "Pace the beats to build suspense — withhold information, escalate danger, end "
        "beats on a hook where possible."
    ),
    "mystery": (
        "Tell this dream through a MYSTERY lens: foreground unanswered questions and "
        "clues. Treat every gap-fill as a clue the dreamer is piecing together rather than "
        "a settled fact."
    ),
    "fantasy": (
        "Tell this dream through a FANTASY lens: foreground the wondrous and impossible "
        "elements, treating dream logic as magic with its own internal rules rather than "
        "something to explain away."
    ),
    "adventure": (
        "Tell this dream through an ADVENTURE lens: foreground momentum, physical action, "
        "and a sense of forward journey — the dreamer as protagonist moving toward "
        "something."
    ),
}


@dataclass
class DreamLenses:
    lenses: dict[str, NarrativeOutput] = field(default_factory=dict)
    # lens name -> error message, for any lens whose LLM call failed — a bad lens should
    # never take down the others, since they're fully independent calls
    errors: dict[str, str] = field(default_factory=dict)


async def generate_lenses(
    graph: DreamGraph,
    session_meta: SessionMeta,
    lens_names: list[str] | None = None,
    model_tier: str = "draft",
) -> DreamLenses:
    names = lens_names or list(LENS_PERSONAS.keys())
    unknown = [n for n in names if n not in LENS_PERSONAS]
    if unknown:
        raise ValueError(f"Unknown narrative lens(es): {unknown}. Known lenses: {list(LENS_PERSONAS)}")

    async def _run_lens(name: str) -> NarrativeOutput:
        config = ReconstructionConfig(
            model_tier=model_tier, lens_persona=LENS_PERSONAS[name], preserve_dream_logic=True
        )
        request = NarrativeReconstructionEngine.input_from_graph(
            graph=graph, session_meta=session_meta, config=config
        )
        # .reconstruct() is a synchronous/blocking network call — push it off the event
        # loop thread so lenses genuinely run concurrently, not one after another.
        return await asyncio.to_thread(NarrativeReconstructionEngine().reconstruct, request)

    results = await asyncio.gather(*[_run_lens(n) for n in names], return_exceptions=True)

    lenses: dict[str, NarrativeOutput] = {}
    errors: dict[str, str] = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            errors[name] = str(result)
        else:
            lenses[name] = result

    return DreamLenses(lenses=lenses, errors=errors)
