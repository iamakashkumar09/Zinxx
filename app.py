"""Integration entrypoint — wires the built modules together behind the FastAPI app.

This file is the one place all module owners' code meets. Keep it thin: it should only
call into modules/*, never contain pipeline logic itself. Run with:
    uvicorn app:app --reload --port 8000

Runtime pipeline (see MODULES.md for the full Architecture.md mapping, including the
modules that are stubbed/not built):

    module1_dream_understanding.process(text)          -> Story
        -> module8_audio_direction.process(story)       -> Story
            -> module9_audio_production.process(story)   -> Story
                -> module10_mixing_timeline.process(story) -> Path (final mp3)

Each arrow is a real function call below — module N's return value is passed directly as
module N+1's argument.
"""

import json
import shutil
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from modules import module1_dream_understanding as module1
from modules import module8_audio_direction as module8
from modules import module9_audio_production as module9
from modules import module10_mixing_timeline as module10
from shared.config import EXAMPLES_DIR, FRONTEND_DIR, OUTPUT_DIR
from shared.models import AudioRequest, AudioResponse, Story, StoryRequest

app = FastAPI(title="Dream to Story")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/story", response_model=Story)
def create_story(req: StoryRequest):
    """Module 1 only — fast, so the UI can show the story before audio finishes."""
    try:
        return module1.process(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Story extraction failed: {exc}") from exc


@app.post("/api/audio", response_model=AudioResponse)
def create_audio(req: AudioRequest):
    """Module 1's output (already in req.story) flows through Modules 8 -> 9 -> 10."""
    story = req.story
    tmp_dir = OUTPUT_DIR / "tmp" / uuid.uuid4().hex
    try:
        story = module8.process(story)          # Module 1 output -> Module 8 input
        story = module9.process(story, tmp_dir)  # Module 8 output -> Module 9 input
        final_path = module10.process(story, OUTPUT_DIR)  # Module 9 output -> Module 10 input
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Audio generation failed: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return AudioResponse(audio_url=f"/output/{final_path.name}", story=story)


@app.get("/api/examples")
def list_examples():
    examples = []
    for manifest_path in sorted(EXAMPLES_DIR.glob("*.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        examples.append(data)
    return examples
