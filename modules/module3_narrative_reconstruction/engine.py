"""
Module 3 — Narrative Reconstruction Engine
engine.py

Public entry point. Everything else in this package is a private implementation
detail of `NarrativeReconstructionEngine.reconstruct()`.

Modules 4 (Dream Layer Engine) and 6 (Multi-Lens Generation) both call this same
class — they just set `config.layer_persona` / `config.lens_persona` before calling.
Module 5 (Ripple Regeneration) calls it with `input.ripple` populated.

Module 2 integration:
  The canonical way to feed Module 2's output into this engine is:

      from modules.module2_dream_graph import build_and_persist_graph
      from modules.module3_narrative_reconstruction import NarrativeReconstructionEngine, SessionMeta

      graph = await build_and_persist_graph(dream_id, user_id, story)
      request = NarrativeReconstructionEngine.input_from_graph(
          graph=graph,
          session_meta=SessionMeta(dream_id=dream_id, user_id=user_id, session_id=session_id),
      )
      output = NarrativeReconstructionEngine().reconstruct(request)
"""

from __future__ import annotations

from .schemas import (
    DreamGraph,
    ReconstructionInput,
    ReconstructionConfig,
    SessionMeta,
    ConversationTurn,
    NarrativeOutput,
    NarrativeBeat,
    GapFill,
    GenerationMetadata,
    new_id,
)
from .prompts import build_system_prompt, build_user_prompt
from .llm_client import NarrativeLLMClient, LLMCallError
from .postprocess import build_provenance_map, detect_contradictions, extract_graph_updates
from .config import DEFAULT_MODELS


class NarrativeReconstructionEngine:
    def __init__(self, llm_client: NarrativeLLMClient | None = None):
        self.llm_client = llm_client or NarrativeLLMClient()

    # ------------------------------------------------------------------
    # Module 2 → Module 3 convenience builder
    # ------------------------------------------------------------------

    @staticmethod
    def input_from_graph(
        graph: DreamGraph,
        session_meta: SessionMeta,
        conversation_context: list[ConversationTurn] | None = None,
        config: ReconstructionConfig | None = None,
    ) -> ReconstructionInput:
        """Construct a ReconstructionInput directly from Module 2's DreamGraph.

        This is the canonical entrypoint when calling Module 3 from app.py or
        from Modules 4/5/6 — it avoids callers having to manually wire up the
        ReconstructionInput dataclass.

        Args:
            graph:                Module 2's DreamGraph (from build_and_persist_graph).
            session_meta:         dream_id / user_id / session_id bundle.
            conversation_context: Optional trimmed conversation turns from Module 1's
                                  Q&A recovery phase. Defaults to empty list.
            config:               Override reconstruction settings. Defaults to
                                  ReconstructionConfig() (draft mode, preserve dream logic).
        """
        return ReconstructionInput(
            dream_graph=graph,
            session_meta=session_meta,
            conversation_context=conversation_context or [],
            config=config or ReconstructionConfig(),
        )

    # ------------------------------------------------------------------
    # Main reconstruction entry point
    # ------------------------------------------------------------------

    def reconstruct(self, request: ReconstructionInput) -> NarrativeOutput:
        config = request.config
        model = DEFAULT_MODELS.FINAL_MODEL if config.model_tier == "final" else DEFAULT_MODELS.DRAFT_MODEL
        temperature = (
            DEFAULT_MODELS.TEMPERATURE_FINAL if config.model_tier == "final" else DEFAULT_MODELS.TEMPERATURE_DRAFT
        )

        system_prompt = build_system_prompt(config)
        user_prompt = build_user_prompt(
            dream_graph=request.dream_graph,
            conversation_context=request.conversation_context,
            ripple=request.ripple,
        )

        try:
            result = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=DEFAULT_MODELS.MAX_OUTPUT_TOKENS,
                max_retries=DEFAULT_MODELS.MAX_RETRIES,
                retry_backoff=DEFAULT_MODELS.RETRY_BACKOFF_SECONDS,
            )
        except LLMCallError as exc:
            # Fail loudly and structurally rather than returning a half-built object —
            # callers (Module 4/5/6) should decide how to handle a hard failure.
            raise

        beats = self._parse_beats(result["parsed"].get("beats", []))
        implied_entities = result["parsed"].get("implied_new_entities", [])

        warnings = detect_contradictions(beats, request.dream_graph)
        graph_updates = extract_graph_updates(implied_entities)
        provenance_map = build_provenance_map(beats)

        metadata = GenerationMetadata(
            model=model,
            temperature=temperature,
            input_tokens=result["usage"].get("input_tokens", 0),
            output_tokens=result["usage"].get("output_tokens", 0),
            latency_seconds=result["latency_seconds"],
            debug=(
                {"system_prompt": system_prompt, "user_prompt": user_prompt, "raw_response": result["raw_text"]}
                if config.debug
                else None
            ),
        )

        return NarrativeOutput(
            narrative_id=new_id("narr"),
            beats=beats,
            graph_updates=graph_updates,
            provenance_map=provenance_map,
            warnings=warnings,
            generation_metadata=metadata,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_beats(raw_beats: list[dict]) -> list[NarrativeBeat]:
        beats: list[NarrativeBeat] = []
        for rb in sorted(raw_beats, key=lambda b: b.get("order", 0)):
            gap_fills = [
                GapFill(
                    gap_id=new_id("gap"),
                    original_gap_description=gf.get("original_gap_description", ""),
                    fill_content=gf.get("fill_content", ""),
                    confidence=float(gf.get("confidence", 0.5)),
                )
                for gf in rb.get("gap_fills", [])
            ]
            beats.append(
                NarrativeBeat(
                    beat_id=new_id("beat"),
                    order=rb.get("order", len(beats) + 1),
                    location_ref=rb.get("location_ref"),
                    characters_present=rb.get("characters_present", []),
                    narrative_text=rb.get("narrative_text", ""),
                    dream_logic_elements=rb.get("dream_logic_elements", []),
                    gap_fills=gap_fills,
                    emotional_tone=rb.get("emotional_tone"),
                )
            )
        return beats
