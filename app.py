"""Integration entrypoint — wires the built modules together behind the FastAPI app.

This file is the one place all module owners' code meets. Keep it thin: it should only
call into modules/*, never contain pipeline logic itself. Run with:
    uvicorn app:app --reload --port 8000

Runtime pipelines:

    /api/story  (Module 1 only — fast preview)
        module1.process(text) -> Story

    /api/dream  (Module 1 → 2 → 3 → 7 — full dream archaeology pipeline)
        module1.process(text)                         -> Story (fast preview, discarded below)
        module2.build_and_persist_graph(...)          -> DreamGraph
        module3.NarrativeReconstructionEngine(...)    -> NarrativeOutput (reconstructed prose beats)
        module7.process(narrative, graph)             -> Story (screenplay, built FROM the
                                                          reconstructed narrative — this is
                                                          what actually feeds /api/audio)
        returns DreamResponse (story + narrative beats)

    /api/audio  (Module 8 → 9 → 10 — audio production from a pre-built Story)
        module8.process(story) -> Story
        module9.process(story, tmp_dir) -> Story
        module10.process(story, OUTPUT_DIR) -> Path (final mp3)

Each arrow is a real function call below — module N's return value is passed directly as
module N+1's argument.

Module 2 (Dream Graph) runs alongside this, off to the side: after /api/story returns,
a background task persists the story into the SQLite-backed graph (characters, locations,
emotions, recurring totems) for future cross-dream recognition. It's best-effort and
non-blocking — nothing in the Module 1 -> 8 -> 9 -> 10 chain reads it back today, so a
Module 2 failure must never slow down or break the actual demo path.
"""

import json
import shutil
import uuid

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from modules import module1_dream_understanding as module1
from modules import module2_dream_graph as module2
from modules import module4_dream_layer_engine as module4
from modules import module5_ripple_regeneration as module5
from modules import module6_multi_lens_generation as module6
from modules import module7_screenplay_conversion as module7
from modules import module8_audio_direction as module8
from modules import module9_audio_production as module9
from modules import module10_mixing_timeline as module10
from modules import module11_qa_consistency as module11
from modules.module2_dream_graph import build_and_persist_graph as build_graph
from modules.module3_narrative_reconstruction import (
    GapFill,
    NarrativeBeat,
    NarrativeOutput,
    NarrativeReconstructionEngine,
    SessionMeta,
    ReconstructionConfig,
)
from modules.module3_narrative_reconstruction.postprocess import build_provenance_map
from shared.config import EXAMPLES_DIR, FRONTEND_DIR, OUTPUT_DIR
from shared.models import (
    AudioRequest,
    AudioResponse,
    DreamEditRequest,
    DreamEditResponse,
    DreamLayersRequest,
    DreamLayersResponse,
    DreamLensesRequest,
    DreamLensesResponse,
    DreamRequest,
    DreamResponse,
    NarrativeBeatResponse,
    QAIssueResponse,
    QAReportResponse,
    Story,
    StoryRequest,
)

USER_ID_COOKIE = "dream_user_id"

app = FastAPI(title="Dream to Story")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
async def _init_dream_graph_db():
    await module2.init_db()


def _get_or_set_user_id(request: Request, response: Response) -> str:
    """Anonymous per-browser id (cookie) so Module 2 can scope totem-matching to
    'this visitor', without needing real accounts/auth for a hackathon demo."""
    user_id = request.cookies.get(USER_ID_COOKIE)
    if not user_id:
        user_id = uuid.uuid4().hex
        response.set_cookie(USER_ID_COOKIE, user_id, max_age=60 * 60 * 24 * 365, httponly=True)
    return user_id


async def _persist_dream_graph(dream_id: str, user_id: str, story: Story) -> None:
    """Best-effort side effect — must never surface as a user-facing failure."""
    try:
        await module2.build_and_persist_graph(dream_id=dream_id, user_id=user_id, story=story)
    except Exception as exc:  # noqa: BLE001
        print(f"[module2_dream_graph] failed to persist graph for dream {dream_id}: {exc}")


def _beats_to_response(beats: list[NarrativeBeat]) -> list[NarrativeBeatResponse]:
    return [
        NarrativeBeatResponse(
            beat_id=b.beat_id,
            order=b.order,
            location_ref=b.location_ref,
            characters_present=b.characters_present,
            narrative_text=b.narrative_text,
            dream_logic_elements=b.dream_logic_elements,
            emotional_tone=b.emotional_tone,
            gap_fills=[
                {
                    "gap_id": gf.gap_id,
                    "original_gap_description": gf.original_gap_description,
                    "fill_content": gf.fill_content,
                    "confidence": gf.confidence,
                    "source": gf.source,
                }
                for gf in b.gap_fills
            ],
        )
        for b in beats
    ]


def _beats_from_response(beats: list[NarrativeBeatResponse]) -> list[NarrativeBeat]:
    """Reverse of _beats_to_response — reconstructs Module 3's dataclasses from what the
    client already has (its own copy of a prior /api/dream response), so ripple
    regeneration (Module 5) doesn't need server-side narrative storage."""
    return [
        NarrativeBeat(
            beat_id=b.beat_id,
            order=b.order,
            location_ref=b.location_ref,
            characters_present=b.characters_present,
            narrative_text=b.narrative_text,
            dream_logic_elements=b.dream_logic_elements,
            emotional_tone=b.emotional_tone,
            gap_fills=[
                GapFill(
                    gap_id=gf.get("gap_id", f"gap_{uuid.uuid4().hex[:8]}"),
                    original_gap_description=gf.get("original_gap_description", ""),
                    fill_content=gf.get("fill_content", ""),
                    confidence=float(gf.get("confidence", 0.5)),
                    source=gf.get("source", "inferred"),
                )
                for gf in b.gap_fills
            ],
        )
        for b in beats
    ]


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Optional voice input for Module 1 — record a dream instead of typing it."""
    try:
        audio_bytes = await file.read()
        text = module1.transcribe(audio_bytes, file.filename or "recording.webm")
        return {"text": text}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc


@app.post("/api/story", response_model=Story)
def create_story(req: StoryRequest, request: Request, response: Response, background_tasks: BackgroundTasks):
    """Module 1 only — fast, so the UI can show the story before audio finishes.

    Also fires off Module 2 (Dream Graph persistence) as a background task after the
    story is ready — see _persist_dream_graph's docstring for why this must stay
    non-blocking and best-effort.
    """
    try:
        story = module1.process(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Story extraction failed: {exc}") from exc

    user_id = _get_or_set_user_id(request, response)
    dream_id = uuid.uuid4().hex
    background_tasks.add_task(_persist_dream_graph, dream_id, user_id, story)

    return story


# ---------------------------------------------------------------------------
# Module 1 → 2 → 3 — full Dream Archaeology pipeline
# ---------------------------------------------------------------------------

@app.post("/api/dream", response_model=DreamResponse)
async def create_dream(req: DreamRequest):
    """Full dream archaeology pipeline: text → Story → DreamGraph → NarrativeOutput.

    Steps:
      1. Module 1 parses the raw dream text into a structured Story.
      2. Module 2 builds and persists the typed Dream Graph (characters, locations,
         objects/totems, emotions, events, transitions) with embedding-based totem
         memory across past sessions.
      3. Module 3 reconstructs the narrative as ordered beats, fills gaps while
         preserving dream logic, and flags inferred details with confidence scores.

    The response's `story` is built by Module 7 FROM the Module 3 narrative (gap-filled,
    dream-logic-preserving) — not the raw Module 1 extraction — so it's ready to feed
    straight into /api/audio and reflects the reconstructed narrative, not just the first
    pass. `narrative_beats` is the underlying reconstructed prose for display.
    """
    dream_id = f"dream_{uuid.uuid4().hex[:12]}"
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    # --- Step 1: Module 1 — dream understanding → structured Story (fast preview) ---
    try:
        story: Story = module1.process(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 1 failed: {exc}") from exc

    # --- Step 2: Module 2 — Dream Graph build + persist ---
    try:
        graph = await build_graph(
            dream_id=dream_id,
            user_id=req.user_id,
            story=story,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 2 (Dream Graph) failed: {exc}") from exc

    # --- Step 3: Module 3 — Narrative Reconstruction ---
    try:
        session_meta = SessionMeta(
            dream_id=dream_id,
            user_id=req.user_id,
            session_id=session_id,
        )
        config = ReconstructionConfig(
            model_tier=req.model_tier,
            preserve_dream_logic=True,
            target_length="medium",
        )
        reconstruction_input = NarrativeReconstructionEngine.input_from_graph(
            graph=graph,
            session_meta=session_meta,
            config=config,
        )
        engine = NarrativeReconstructionEngine()
        narrative_output = engine.reconstruct(reconstruction_input)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 3 (Narrative Reconstruction) failed: {exc}") from exc

    # --- Step 4: Module 7 — Screenplay Conversion (narrative beats -> Story) ---
    # Replaces the Module 1 fast-preview `story` with one built from the reconstructed
    # narrative, so /api/audio actually voices the gap-filled version, not the first pass.
    try:
        story = module7.process(narrative_output, graph, title_hint=story.title)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 7 (Screenplay Conversion) failed: {exc}") from exc

    # --- Assemble response ---
    beats = _beats_to_response(narrative_output.beats)

    metadata = None
    if narrative_output.generation_metadata:
        m = narrative_output.generation_metadata
        metadata = {
            "model": m.model,
            "input_tokens": m.input_tokens,
            "output_tokens": m.output_tokens,
            "latency_seconds": m.latency_seconds,
        }

    return DreamResponse(
        dream_id=dream_id,
        story=story,
        narrative_beats=beats,
        warnings=narrative_output.warnings,
        graph_updates=[upd.payload for upd in narrative_output.graph_updates],
        generation_metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Module 1 → 2 → 4 — Dream Layer Engine (Inception-style reality layers)
# ---------------------------------------------------------------------------

@app.post("/api/dream/layers", response_model=DreamLayersResponse)
async def create_dream_layers(req: DreamLayersRequest):
    """Same dream, reconstructed across multiple psychological layers (conscious dream /
    subconscious memory / hidden fear / symbolic truth by default) in parallel. Text-only —
    pick a layer's narrative_beats and pass it through Module 7 + /api/audio separately if
    you want a specific layer voiced."""
    dream_id = f"dream_{uuid.uuid4().hex[:12]}"
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    try:
        story = module1.process(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 1 failed: {exc}") from exc

    try:
        graph = await build_graph(dream_id=dream_id, user_id=req.user_id, story=story)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 2 (Dream Graph) failed: {exc}") from exc

    try:
        session_meta = SessionMeta(dream_id=dream_id, user_id=req.user_id, session_id=session_id)
        result = await module4.process(
            graph, session_meta, layer_names=req.layer_names, model_tier=req.model_tier
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 4 (Dream Layer Engine) failed: {exc}") from exc

    return DreamLayersResponse(
        dream_id=dream_id,
        layers={name: _beats_to_response(output.beats) for name, output in result.layers.items()},
        totem_cross_references=result.totem_cross_references,
        errors=result.errors,
    )


# ---------------------------------------------------------------------------
# Module 1 → 2 → 6 — Multi-Lens Narrative Generation
# ---------------------------------------------------------------------------

@app.post("/api/dream/lenses", response_model=DreamLensesResponse)
async def create_dream_lenses(req: DreamLensesRequest):
    """Same dream, told through multiple genre lenses (psychological / thriller / mystery
    / fantasy / adventure by default) in parallel."""
    dream_id = f"dream_{uuid.uuid4().hex[:12]}"
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    try:
        story = module1.process(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 1 failed: {exc}") from exc

    try:
        graph = await build_graph(dream_id=dream_id, user_id=req.user_id, story=story)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 2 (Dream Graph) failed: {exc}") from exc

    try:
        session_meta = SessionMeta(dream_id=dream_id, user_id=req.user_id, session_id=session_id)
        result = await module6.process(
            graph, session_meta, lens_names=req.lens_names, model_tier=req.model_tier
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 6 (Multi-Lens Generation) failed: {exc}") from exc

    return DreamLensesResponse(
        dream_id=dream_id,
        lenses={name: _beats_to_response(output.beats) for name, output in result.lenses.items()},
        errors=result.errors,
    )


# ---------------------------------------------------------------------------
# Module 5 → 7 — Interactive Ripple Regeneration
# ---------------------------------------------------------------------------

@app.post("/api/dream/edit", response_model=DreamEditResponse)
async def edit_dream(req: DreamEditRequest):
    """Edit one Dream Graph node (from a prior /api/dream call) and regenerate only the
    narrative beats that causally depend on it — everything else is copied through
    unchanged by Module 3's own ripple-aware prompt. Re-runs Module 7 on the result so the
    response's `story` is immediately ready for /api/audio.

    The server doesn't persist NarrativeOutput between requests, so send back the
    `narrative_beats` you got from /api/dream (or a previous /api/dream/edit) as
    `previous_narrative_beats` — same stateless pattern /api/audio uses for Story."""
    previous_beats = _beats_from_response(req.previous_narrative_beats)
    previous_narrative = NarrativeOutput(
        narrative_id=f"narr_prev_{uuid.uuid4().hex[:8]}",
        beats=previous_beats,
        provenance_map=build_provenance_map(previous_beats),
    )

    try:
        result = await module5.process(
            dream_id=req.dream_id,
            user_id=req.user_id,
            session_id=req.session_id,
            node_id=req.node_id,
            previous_narrative=previous_narrative,
            new_label=req.new_label,
            new_attributes=req.new_attributes or None,
            model_tier=req.model_tier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 5 (Ripple Regeneration) failed: {exc}") from exc

    try:
        story = module7.process(result.narrative, result.graph)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Module 7 (Screenplay Conversion) failed: {exc}") from exc

    return DreamEditResponse(
        dream_id=req.dream_id,
        story=story,
        narrative_beats=_beats_to_response(result.narrative.beats),
        changed_node_ids=result.changed_node_ids,
        affected_beat_ids=result.affected_beat_ids,
    )


# ---------------------------------------------------------------------------
# Module 8 → 9 → 10 — audio production from a pre-built Story (unchanged)
# ---------------------------------------------------------------------------

@app.post("/api/audio", response_model=AudioResponse)
def create_audio(req: AudioRequest):
    """Module 1's output (already in req.story) flows through Modules 8 -> 9 -> 11 -> 10."""
    story = req.story
    tmp_dir = OUTPUT_DIR / "tmp" / uuid.uuid4().hex
    try:
        story = module8.process(story)          # Module 1 output -> Module 8 input
        story = module9.process(story, tmp_dir)  # Module 8 output -> Module 9 input

        # Module 11 — advisory QA pass over the finished screenplay + audio metadata
        # (durations, cue list), per Architecture.md. Must never block the render: a
        # network hiccup or a found issue is just surfaced in the response, not fatal.
        qa_report = None
        try:
            report = module11.process(story)
            qa_report = QAReportResponse(
                consistency_score=report.consistency_score,
                issues=[
                    QAIssueResponse(
                        scene_id=i.scene_id,
                        line_index=i.line_index,
                        category=i.category,
                        severity=i.severity,
                        description=i.description,
                    )
                    for i in report.issues
                ],
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[module11_qa_consistency] review failed (non-fatal): {exc}")

        final_path = module10.process(story, OUTPUT_DIR)  # Module 9 output -> Module 10 input
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Audio generation failed: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return AudioResponse(audio_url=f"/output/{final_path.name}", story=story, qa_report=qa_report)


# ---------------------------------------------------------------------------
# Examples listing (unchanged)
# ---------------------------------------------------------------------------

@app.get("/api/examples")
def list_examples():
    examples = []
    for manifest_path in sorted(EXAMPLES_DIR.glob("*.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        examples.append(data)
    return examples
