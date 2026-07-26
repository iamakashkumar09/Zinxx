# Dream to Story

Turn a free-text dream or memory description into a short, fully-produced cinematic audio
drama — multiple character voices, emotion-matched delivery, ambient sound design, and
timed sound effects, mixed into one final audio file.

Built per `Dream-to-Story-Build-Spec.md`. Module boundaries follow
`Dream-to-Story-Architecture.md` — all 11 of its modules are implemented; see
**[MODULES.md](MODULES.md)** for the full module map, ownership split, and how each one
fits together. Pipeline: OpenAI (dream understanding, narrative reconstruction, screenplay
conversion, audio direction, QA review) → HuggingFace emotion classifier → edge-tts
(voices) → procedural numpy/scipy sound design → pydub (mix). Voice input (optional)
transcribes via Groq's free-tier Whisper.

## 1. Setup

### Prerequisites

- Python 3.12 (the `myenv/` venv is already created at the project root)
- **ffmpeg on PATH** — required by `pydub` for audio encode/decode/export.
  - Windows: `winget install ffmpeg` or `choco install ffmpeg`, then restart your terminal.
  - Verify with: `ffmpeg -version`
- An OpenAI API key (platform.openai.com/api-keys — used by Module 1 and Module 8; this is
  the quality-critical path so it's worth spending real budget here).
- A Groq API key (free at console.groq.com/keys — used only for the optional mic/voice
  input's transcription). edge-tts needs no key.

### Install

```powershell
myenv\Scripts\pip install -r requirements.txt
copy .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-... and GROQ_API_KEY=gsk_...
```

`OPENAI_MODEL` defaults to `gpt-4o`. If you want to cut cost on the less quality-sensitive
Module 8 (performance direction), you can point that call at a cheaper model independently
— see the note in `modules/module8_audio_direction/performance_direction.py`.

Module 2 (Dream Graph) needs no setup at all — it uses a local SQLite file
(`output/dream_graph.db`, created automatically on first run) rather than a real database,
so there's no `DREAM_DB_URL`/host/port/password to configure.

## 2. Run

```powershell
myenv\Scripts\uvicorn app:app --reload --port 8000
```

Open **http://localhost:8000** — the FastAPI app serves the frontend directly (no separate
dev server needed).

Flow: type a dream (or tap the mic button and speak it — transcribed via Groq Whisper) →
**Generate** → story structure (title/characters/scenes) appears in a few seconds →
voices/sound design/mixing runs → final mixed track appears in an `<audio>` player with a
Download link.

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
  openai_client.py            shared OpenAI client factory (used by Module 1 and Module 8)
  llm_client.py                shared Groq client factory (used only by Module 1's voice transcription)
modules/
  module1_dream_understanding/   BUILT  — OpenAI call, raw text -> structured Story (+ optional voice input via Groq Whisper)
  module2_dream_graph/           BUILT  — SQLite graph + OpenAI embeddings, background side-effect after /api/story
  module3_narrative_reconstruction/ BUILT — OpenAI, gap-filling narrative reconstruction, /api/dream
  module4_dream_layer_engine/    BUILT  — parallel reality-layer orchestration over Module 3, /api/dream/layers
  module5_ripple_regeneration/   BUILT  — graph versioning + provenance diffing, /api/dream/edit
  module6_multi_lens_generation/ BUILT  — parallel genre-lens orchestration over Module 3, /api/dream/lenses
  module7_screenplay_conversion/ BUILT  — OpenAI, narrative beats -> Story, feeds Modules 8-10
  module8_audio_direction/       BUILT  — emotion scoring + OpenAI performance direction
  module9_audio_production/      BUILT  — edge-tts voices + mood-driven procedural SFX/BGM + cue timing
  module10_mixing_timeline/      BUILT  — pydub mixing, final mp3 export
  module11_qa_consistency/       BUILT  — advisory OpenAI QA pass, runs inside /api/audio
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
- **Sound effects and background music are procedurally synthesized**, not sampled — this
  keeps the whole stack free-tier/offline-capable per the spec's non-functional
  requirements, at the cost of some realism (e.g. "footstep" is a shaped low-pass thud, not
  a real recording). Both are mood-aware: `modules/module9_audio_production/mood.py` maps
  each scene's `emotional_tone` to musical parameters (root note, major/minor/dissonant
  interval, brightness, tremolo, distortion) that shape both the ambience texture
  (`sfx_synth.py`) and a dedicated BGM chord pad generated per scene (`music_synth.py`) —
  so a "furious" scene actually sounds tense/aggressive and a "peaceful" one sounds warm,
  rather than every scene defaulting to the same generic noise bed.
- Voice delivery prosody (rate/pitch) is driven by the same emotion scores, with an
  intensity floor so even a moderately-confident emotion reads clearly instead of fading
  toward neutral — see the note in `voice_generation.py`.
- **Two-phase API** (`/api/story` then `/api/audio`) lets the UI show the extracted story
  immediately while the slower audio stage (TTS + SFX + mixing) runs, per the spec's UX
  requirement.
- Each character gets a consistent voice from a small pool of `edge-tts` neural voices,
  assigned in first-seen order.
- All 11 `Dream-to-Story-Architecture.md` modules are implemented. Only Modules 1, 8, 9,
  10 sit in the default demo path (`/api/story` → `/api/audio`) — Modules 2-7 and 11 are
  reachable through the dedicated `/api/dream`, `/api/dream/layers`, `/api/dream/lenses`,
  and `/api/dream/edit` endpoints (see MODULES.md for exactly how each fits together), so
  none of them can break the simple demo path even though they're all real, tested code.
  Module 2 (Dream Graph) persists every generated story into a local SQLite database
  (`output/dream_graph.db`, auto-created, no setup) and recognizes recurring characters/
  locations across a browser session via OpenAI embeddings.

## 7. Troubleshooting

- **"OPENAI_API_KEY is not set"** — copy `.env.example` to `.env` and fill in the key.
- **"GROQ_API_KEY is not set"** (only affects the mic/voice-input button) — same fix, this
  key is separate from `OPENAI_API_KEY` and only used by `transcription.py`.
- **pydub / ffmpeg errors on export** — confirm `ffmpeg -version` works in the same shell
  you're running uvicorn from.
- **First request is slow** — the HuggingFace emotion model downloads on first use
  (cached after that in `~/.cache/huggingface`).
- **edge-tts fails / times out** — it calls Microsoft's free endpoint over the internet; no
  key needed, but it does need connectivity. If offline, swap `module9_audio_production/
  voice_generation.py` for a local TTS (e.g. `pyttsx3`) as a fallback — the rest of the
  pipeline is unaffected since it only depends on `line.audio_path` / `line.duration_ms`
  being populated.
