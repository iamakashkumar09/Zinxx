# Module Map

The folder structure under `modules/` mirrors `Dream-to-Story-Architecture.md`'s 11 modules
exactly, one folder per module, numbered to match. This file is the integration contract:
what's built, what talks to what, and where to plug in what isn't built yet.

## Status at a glance

| # | Folder | Architecture.md module | Status |
|---|---|---|---|
| 1 | `module1_dream_understanding/` | Dream Understanding & Conversational Recovery | **Built** (OpenAI + Groq Whisper for voice input) |
| 2 | `module2_dream_graph/` | Dream Graph | **Built** (SQLite + OpenAI embeddings) — runs as a background side-effect, not in the audio critical path |
| 3 | `module3_narrative_reconstruction/` | Narrative Reconstruction Engine | Stub — folded into Module 1 |
| 4 | `module4_dream_layer_engine/` | Dream Layer Engine (Inception-style) | Stub — not implemented |
| 5 | `module5_ripple_regeneration/` | Interactive Ripple Regeneration | Stub — not implemented |
| 6 | `module6_multi_lens_generation/` | Multi-Lens Narrative Generation | Stub — not implemented |
| 7 | `module7_screenplay_conversion/` | Screenplay Conversion | Stub — folded into Module 1 |
| 8 | `module8_audio_direction/` | Audio Direction Engine | **Built** (OpenAI + local HF classifier) |
| 9 | `module9_audio_production/` | Audio Production | **Built** (edge-tts + procedural SFX) |
| 10 | `module10_mixing_timeline/` | Mixing & Timeline Composition | **Built** (pydub) |
| 11 | `module11_qa_consistency/` | Quality/Consistency Review | Stub — not implemented |

Every stub folder's `__init__.py` explains, in its own docstring, why it's skipped and
where it would plug into the pipeline if someone picks it up.

## Runtime pipeline (what actually runs on every request)

The audio critical path is Modules 1, 8, 9, 10. Each one's output is literally the next
one's input — see `app.py`, which is the one file where all of them meet:

```python
story = module1_dream_understanding.process(text)        # text -> Story
story = module8_audio_direction.process(story)            # Story -> Story (+emotion, +direction)
story = module9_audio_production.process(story, tmp_dir)  # Story -> Story (+audio_path, +position_ms)
final_path = module10_mixing_timeline.process(story, out) # Story -> Path (final mp3)
```

**Module 2 runs alongside this, not inside it.** Right after `/api/story` returns (in
`app.py`'s `create_story`), a FastAPI `BackgroundTask` calls
`module2_dream_graph.build_and_persist_graph(dream_id, user_id, story)` — it persists
characters/locations/emotions/events into SQLite and checks them against the same
browser's past dreams (scoped via an anonymous `dream_user_id` cookie) for recurring
totems. This is fire-and-forget: it runs *after* the HTTP response is already sent, and
any failure is caught and logged, never raised — nothing downstream (Modules 8-10) reads
the graph back today, so Module 2 breaking must never break the demo.

Text generation (Module 1 extraction, Module 8 direction) runs on **OpenAI** (`gpt-4o` by
default), matching the architecture doc directly. Voice input transcription stays on
**Groq's free-tier Whisper** (separate concern, separate cost — no reason to spend OpenAI
budget on it). Audio production uses **edge-tts** + **procedural numpy/scipy synthesis**
instead of `gpt-4o-mini-tts` + Stable Audio Open/AudioGen. Module 2 uses **SQLite**
instead of Postgres+pgvector (see its own section below) — same module boundaries, mixed
free/local stack depending on what each piece needs.

## The shared contract: `shared/models.py`

The `Story` object (and its nested `Character`, `Scene`, `Line`, `SoundCue`) is the only
thing that crosses module boundaries. If you're changing a field name or type in here,
tell the other 3 people first — every module reads and writes this same object.

- Module 1 **creates** `Story` (title, characters, scenes, lines, sound_cues — `prompt`/`position` set, everything else `None`)
- Module 8 **fills in** `Line.emotion_scores` + `Line.performance_direction`
- Module 9 **fills in** `Line.audio_path` + `Line.duration_ms`, and `SoundCue.position_ms`
- Module 10 **reads** the fully-populated `Story` and produces the final audio file (doesn't mutate `Story` further)
- Module 2 **reads** `Story` right after Module 1 (the version with no emotion/audio fields
  filled in yet) and builds a separate `DreamGraph` object (`modules/module2_dream_graph/models.py`)
  from it — it never mutates `Story` itself, so it's invisible to Modules 8-10

Other shared code (not module-specific, anyone can use):
- `shared/config.py` — env vars + mixing constants (`OPENAI_API_KEY`, `GROQ_API_KEY`, `DREAM_DB_URL`, `LINE_GAP_MS`, gain levels, etc.). `DREAM_DB_URL` defaults to a local SQLite file (`output/dream_graph.db`) — no setup needed, only override it if you deliberately want a different backend.
- `shared/openai_client.py` — `get_client()` (sync, used by Module 1's `story_extraction.py` and Module 8's `performance_direction.py`) and `get_async_client()` (async, used by Module 2's `totems.py` for embeddings). Both are lazy singletons — built on first use, not at import time, so importing these modules never crashes even before `.env` has loaded.
- `shared/llm_client.py` — the Groq client factory, used only by Module 1's `transcription.py` (voice input)

## Folder-by-folder

### `module1_dream_understanding/` — Built
- `story_extraction.py` — the OpenAI call (`OPENAI_MODEL`, default `gpt-4o`) + prompt.
  Public API: `process(raw_text) -> Story`
- `transcription.py` — optional voice input (Architecture.md's `gpt-4o-mini-transcribe`
  equivalent), using Groq's hosted `whisper-large-v3-turbo` (kept on Groq — free, already
  working, not the piece that needed a quality upgrade). Public API:
  `transcribe(file_bytes, filename) -> str`. Wired to a mic button in the frontend
  (`POST /api/transcribe`) — records via `MediaRecorder`, transcribes, fills the textarea;
  output flows into `process()` exactly like typed text.
- Also does Architecture.md Modules 3 (Narrative Reconstruction) and 7 (Screenplay
  Conversion) inline, in the same prompt/call. Module 2 (Dream Graph) exists now, but
  splitting this into a real multi-step pipeline that reads/writes the graph mid-generation
  is still future work — today Module 2 only runs afterward, as a side effect.

### `module8_audio_direction/` — Built
- `emotion_scoring.py` — local HuggingFace classifier (`j-hartmann/emotion-english-distilroberta-base`), no API
- `performance_direction.py` — OpenAI call (same `OPENAI_MODEL` as Module 1), one per scene, batches all lines in that scene
- Public API: `process(story) -> Story`

### `module9_audio_production/` — Built
- `voice_generation.py` — edge-tts, one consistent voice per character, prosody (rate/pitch)
  driven by Module 8's emotion scores. Prosody ranges were deliberately pushed up from the
  first version — at the original scale, a moderately-confident emotion score (~0.5, the
  common case) produced a barely-audible rate/pitch nudge. There's also an intensity floor
  now so even a middling-confidence emotion still clearly colors the delivery instead of
  fading toward neutral.
- `mood.py` — the shared emotion -> musical-mood table (`classify_mood`, `mood_params`)
  used by both generators below, so "what does fear sound like" is defined once, not
  duplicated. Maps `emotional_tone` text to a mood (joy/warm/calm/sad/mysterious/fear/
  anger/surprise/neutral) and a `MoodParams` tuple (root note, interval, brightness,
  tremolo rate, detune, distortion).
- `dsp.py` — shared low-level signal-generation primitives (noise, filters, envelopes,
  normalize/export) used by both `sfx_synth.py` and `music_synth.py`.
- `sfx_synth.py` — procedural ambience + one-shot SFX. Ambience texture (wind/rain/fire/
  room/city/default) is picked by literal keywords in the cue prompt, same as before, but
  is now **also** shaped by the scene's `emotional_tone` via `mood.py` — brightness
  (lowpass cutoff), movement (tremolo rate), and grit (soft-clip distortion for anger) all
  shift with mood, so the same "wind" cue sounds calm, tense, or aggressive depending on
  what's actually happening in the scene, instead of sounding identical every time.
- `music_synth.py` — **new**: procedural background music. A sustained chord pad (stacked
  sine layers: sub, root, third, fifth) whose root note, major/minor/dissonant interval,
  brightness, tremolo, and distortion are entirely driven by `emotional_tone` via
  `mood.py`. This is what the architecture doc calls "Background music" under Module 9 —
  previously unbuilt; every scene now gets one of these, not just scenes with an explicit
  ambient sound cue, so there's always mood-appropriate coloring under the dialogue rather
  than silence or generic room tone.
- `sound_cues.py` — resolves "before/after line N" hints into millisecond offsets using real TTS durations
- Public API: `process(story, tmp_dir) -> Story`

### `module10_mixing_timeline/` — Built
- `mixing.py` — pydub: per-scene dialogue + **BGM bed (mood-driven, every scene)** +
  ambience underlay (keyword + mood driven, only scenes with an ambient cue) + one-shot
  overlay, scene concat with crossfade, normalize, export mp3. Gain layers: dialogue at
  full level, ambience at `AMBIENCE_GAIN_DB` (-20dB), BGM quieter still at `BGM_GAIN_DB`
  (-25dB, `shared/config.py`) — mood coloring under everything, never fighting the voice.
- Public API: `process(story, output_dir) -> Path`

### `module2_dream_graph/` — Built
- `models.py` — the graph schema: 6 node types (character, location, object_totem,
  emotion, event, transition) and 6 typed edges (feels, owns, transforms_into,
  happens_before, located_at, appears_in), per Architecture.md's spec.
- `builder.py` — turns a `Story` into typed nodes/edges (`build_graph`). Note: never
  creates `object_totem` nodes today — Module 1's `Story` schema has no "objects" field,
  so totem-matching currently only ever operates on `character`/`location` nodes. Extending
  this needs a Module 1 schema change (a shared-contract decision, not a Module 2-only fix).
- `totems.py` — `link_recurring_symbols(graph)`: embeds every character/location/
  object_totem node (OpenAI `text-embedding-3-small`) and checks it against this user's
  past nodes; tags `matched_totem_id`/`matched_totem_similarity`/`is_recurring_symbol` on a
  match ≥ 0.86 cosine similarity.
- `db.py` — **local SQLite** (`output/dream_graph.db`, auto-created — no server, URL, port,
  or password to configure). Embeddings are stored as JSON and compared with numpy cosine
  similarity in Python rather than a vector index — completely fine at hackathon scale
  (a handful of nodes per user), swap this file alone if that ever needs to change.
- Public API: `await build_and_persist_graph(dream_id, user_id, story) -> DreamGraph`.
  **Order matters inside this function**: `persist_graph()` (INSERT) must run before
  `link_recurring_symbols()` (which does per-node UPDATEs) — getting this backwards silently
  no-ops every embedding write, which is exactly the bug that shipped originally and was
  fixed by reordering + making `store_node_embedding` also persist the match fields it was
  previously dropping.
- Wired into `app.py` as a background task after `/api/story` — see the runtime pipeline
  section above. It does **not** feed into `Story` or the Module 8-10 chain; it's a parallel
  persistence path for future features (Module 4's Dream Layer Engine, Module 5's Ripple
  Regeneration) that would read the graph back. Today nothing does.

### `module4_dream_layer_engine/`, `module5_ripple_regeneration/`, `module6_multi_lens_generation/`, `module11_qa_consistency/` — Stubs
Each has a docstring explaining the intended design per Architecture.md and what it would
depend on. `module6_multi_lens_generation` is the easiest one to pick up first (no
dependency on the others); `module4_dream_layer_engine` is the architecture doc's own pick
for highest-value "if you have time left" feature, and now that Module 2 is built, it's
unblocked.

### `module3_narrative_reconstruction/`, `module7_screenplay_conversion/` — Stubs (folded into Module 1)
These exist as folders for structural completeness but their logic currently lives inside
Module 1's single prompt. Module 2 (Dream Graph) exists now, so splitting these out to
actually read/write it mid-generation is unblocked — just not done yet.

## Suggested ownership

- **Person A:** `module1_dream_understanding/` — prompt engineering, JSON reliability, story quality
- **Person B:** `module8_audio_direction/` — emotion scoring + performance direction prompt quality
- **Person C:** `module9_audio_production/` — voice casting, prosody mapping, SFX synthesis quality
- **Person D:** `module10_mixing_timeline/` + `app.py` (integration) + `frontend/`
- **Person E:** `module2_dream_graph/` — graph schema, totem-matching quality/threshold tuning, and eventually extending Module 1's schema to extract actual objects/totems (currently the graph only has character/location nodes to match on — see that folder's section above)

Whoever owns `app.py` is the integration point — when two modules' contracts need to
change together (e.g. a new `Story` field), that person coordinates the merge.
