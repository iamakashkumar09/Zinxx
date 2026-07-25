# Dream to Story

Turn a free-text dream or memory description into a short, fully-produced cinematic audio
drama — multiple character voices, emotion-matched delivery, ambient sound design, and
timed sound effects, mixed into one final audio file.

Built per `Dream-to-Story-Build-Spec.md`. Module boundaries follow
`Dream-to-Story-Architecture.md` — see **[MODULES.md](MODULES.md)** for the full module
map, ownership split, and what's built vs. stubbed. Pipeline: Groq (dream understanding,
audio direction) → HuggingFace emotion classifier → edge-tts (voices) → procedural
numpy/scipy sound design → pydub (mix).

## 1. Setup

### Prerequisites

- Python 3.12 (the `myenv/` venv is already created at the project root)
- **ffmpeg on PATH** — required by `pydub` for audio encode/decode/export.
  - Windows: `winget install ffmpeg` or `choco install ffmpeg`, then restart your terminal.
  - Verify with: `ffmpeg -version`
- A Groq API key (free at console.groq.com/keys — used by Module 1 and Module 8).
  edge-tts needs no key.

### Install

```powershell
myenv\Scripts\pip install -r requirements.txt
copy .env.example .env
# then edit .env and set GROQ_API_KEY=gsk_...
```

`GROQ_MODEL` defaults to `llama-3.1-8b-instant` — chosen for its much higher free-tier
daily quota (the larger `llama-3.3-70b-versatile` hits its 100k TPD cap fast once a few
people on the team are testing against it). If you want higher quality and have quota
budget left, swap in `llama-3.3-70b-versatile`. Run `client.models.list()` (see
`shared/llm_client.py`) to see every model your key currently has access to — Groq's free
tier quota is tracked **per model**, so switching models is the fastest way to get
unblocked mid-demo if you hit a rate limit.

## 2. Run

```powershell
myenv\Scripts\uvicorn app:app --reload --port 8000
```

Open **http://localhost:8000** — the FastAPI app serves the frontend directly (no separate
dev server needed).

Flow: type a dream → **Generate** → story structure (title/characters/scenes) appears in a
few seconds → voices/sound design/mixing runs → final mixed track appears in an `<audio>`
player with a Download link.

## 3. Test story extraction in isolation

Before touching anything else, verify Module 1 (the highest-risk, highest-priority piece)
works reliably across varied inputs:

```powershell
myenv\Scripts\python scripts\test_story_extraction.py
```

This runs every sample in `samples/sample_dreams.txt` (short, long, multi-character,
single-character, and an intentionally empty one) through Module 1 and reports pass/fail.

## 4. Prepare the demo-safe fallback (do this before judging, while you have good wifi)

```powershell
myenv\Scripts\python scripts\pregenerate_examples.py
```

This runs 3 sample dreams through the **entire built pipeline** (Modules 1 → 8 → 9 → 10)
and saves the finished audio + story JSON into `output/examples/`. The frontend
automatically shows "Load a pre-made example" buttons (via `GET /api/examples`) that play
these instantly — no live API calls — in case live generation is slow or the venue wifi
drops during your demo.

## 5. Project structure

```
app.py                        Integration entrypoint — wires modules together, FastAPI routes
shared/
  models.py                   Story/Scene/Line/SoundCue — the contract every module reads/writes
  config.py                   env vars + shared mixing constants
  llm_client.py               shared Groq client factory (used by Module 1 and Module 8)
modules/
  module1_dream_understanding/   BUILT  — Groq call, raw text -> structured Story
  module2_dream_graph/           stub   — not implemented
  module3_narrative_reconstruction/ stub — folded into Module 1
  module4_dream_layer_engine/    stub   — not implemented
  module5_ripple_regeneration/   stub   — not implemented
  module6_multi_lens_generation/ stub   — not implemented
  module7_screenplay_conversion/ stub   — folded into Module 1
  module8_audio_direction/       BUILT  — emotion scoring + Groq performance direction
  module9_audio_production/      BUILT  — edge-tts voices + procedural SFX + cue timing
  module10_mixing_timeline/      BUILT  — pydub mixing, final mp3 export
  module11_qa_consistency/       stub   — not implemented
frontend/
  index.html / app.js / style.css   vanilla JS, no build step
samples/sample_dreams.txt    8 varied test inputs
scripts/
  test_story_extraction.py   isolated Module 1 test loop
  pregenerate_examples.py    builds the demo fallback examples, runs the full built pipeline
output/                      generated audio (gitignored, safe to clear)
MODULES.md                   full module map, contracts, and ownership — read this first
```

See **[MODULES.md](MODULES.md)** for exactly how each module's output feeds the next one's
input, and where the not-yet-built modules would plug in if your team has time for them.

## 6. Design notes / known simplifications (hackathon scope)

- **Ambience "ducking"** is a fixed low-gain underlay (-20dB) rather than true sidechain
  compression — simpler and good enough for a short demo track; documented in `mixing.py`.
- **Sound effects are procedurally synthesized**, not sampled — this keeps the whole stack
  free-tier/offline-capable per the spec's non-functional requirements, at the cost of
  some realism (e.g. "footstep" is a shaped low-pass thud, not a real recording).
- **Two-phase API** (`/api/story` then `/api/audio`) lets the UI show the extracted story
  immediately while the slower audio stage (TTS + SFX + mixing) runs, per the spec's UX
  requirement.
- Each character gets a consistent voice from a small pool of `edge-tts` neural voices,
  assigned in first-seen order.
- Modules 2-7 (Dream Graph, Dream Layer Engine, Ripple Regeneration, Multi-Lens, etc.) are
  the stretch-goal features from `Dream-to-Story-Architecture.md` — not built, but stubbed
  with clear docstrings in `modules/` for whoever wants to pick one up.

## 7. Troubleshooting

- **"GROQ_API_KEY is not set"** — copy `.env.example` to `.env` and fill in the key.
- **pydub / ffmpeg errors on export** — confirm `ffmpeg -version` works in the same shell
  you're running uvicorn from.
- **First request is slow** — the HuggingFace emotion model downloads on first use
  (cached after that in `~/.cache/huggingface`).
- **edge-tts fails / times out** — it calls Microsoft's free endpoint over the internet; no
  key needed, but it does need connectivity. If offline, swap `module9_audio_production/
  voice_generation.py` for a local TTS (e.g. `pyttsx3`) as a fallback — the rest of the
  pipeline is unaffected since it only depends on `line.audio_path` / `line.duration_ms`
  being populated.
