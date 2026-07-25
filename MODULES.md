# Module Map

The folder structure under `modules/` mirrors `Dream-to-Story-Architecture.md`'s 11 modules
exactly, one folder per module, numbered to match. This file is the integration contract:
what's built, what talks to what, and where to plug in what isn't built yet.

## Status at a glance

| # | Folder | Architecture.md module | Status |
|---|---|---|---|
| 1 | `module1_dream_understanding/` | Dream Understanding & Conversational Recovery | **Built** (OpenAI + Groq Whisper for voice input) |
| 2 | `module2_dream_graph/` | Dream Graph | **Built** (SQLite + OpenAI embeddings) — runs as a background side-effect, not in the audio critical path |
| 3 | `module3_narrative_reconstruction/` | Narrative Reconstruction Engine | **Built** (OpenAI, mock-mode fallback with no key) |
| 4 | `module4_dream_layer_engine/` | Dream Layer Engine (Inception-style) | **Built** (orchestrates Module 3 in parallel, `/api/dream/layers`) |
| 5 | `module5_ripple_regeneration/` | Interactive Ripple Regeneration | **Built** (graph versioning + provenance diffing, `/api/dream/edit`) |
| 6 | `module6_multi_lens_generation/` | Multi-Lens Narrative Generation | **Built** (orchestrates Module 3 in parallel, `/api/dream/lenses`) |
| 7 | `module7_screenplay_conversion/` | Screenplay Conversion | **Built** (OpenAI) — converts Module 3's narrative beats into a Story for Modules 8-10 |
| 8 | `module8_audio_direction/` | Audio Direction Engine | **Built** (OpenAI + local HF classifier) |
| 9 | `module9_audio_production/` | Audio Production | **Built** (edge-tts + procedural SFX) |
| 10 | `module10_mixing_timeline/` | Mixing & Timeline Composition | **Built** (pydub) |
| 11 | `module11_qa_consistency/` | Quality/Consistency Review | **Built** (OpenAI, advisory-only) — runs inside `/api/audio` between Modules 9 and 10 |

All 11 modules from Architecture.md are built. Modules 3, 4, 5, 6, 7, 11 are
stubless-by-default in the sense that none of them are load-bearing for the core demo
path (`/api/story` → `/api/audio`, Modules 1/8/9/10) — they're reachable through the
dedicated `/api/dream*` endpoints and Module 11's advisory pass, all detailed below.

## Runtime pipeline (what actually runs on every request)

There are two entry points into the text pipeline, both defined in `app.py`:

**`/api/story` — fast preview.** Module 1 only. This is what the frontend calls today for
the sub-10-second "show me the story while audio generates" UX.
```python
story = module1_dream_understanding.process(text)   # text -> Story
```
Right after this returns, a FastAPI `BackgroundTask` calls
`module2_dream_graph.build_and_persist_graph(dream_id, user_id, story)` — persists
characters/locations/emotions/events into SQLite and checks them against the same
browser's past dreams (scoped via an anonymous `dream_user_id` cookie) for recurring
totems. Fire-and-forget: runs *after* the response is sent, failures are caught and
logged, never raised.

**`/api/dream` — the full dream archaeology pipeline.** Modules 1 → 2 → 3 → 7, all
synchronous, returning a `Story` that's actually built from the *reconstructed* narrative:
```python
story = module1.process(text)                              # text -> Story (used only as a title hint below)
graph = await module2.build_and_persist_graph(...)          # Story -> DreamGraph
narrative = NarrativeReconstructionEngine().reconstruct(...) # DreamGraph -> NarrativeOutput (prose beats)
story = module7_screenplay_conversion.process(narrative, graph, title_hint=story.title)  # -> Story
```
Module 7 is the missing link that used to make Module 3's output a dead end: it turns
each reconstructed narrative beat's *prose* into actual dialogue lines + sound cues,
pulling character/location facts straight from the graph (authoritative, no need to ask
an LLM to re-derive a name it already knows). The resulting `Story` is exactly the same
shape Module 1 produces directly — feed it to `/api/audio` and Modules 8-10 don't know or
care which path it came from.

**Both paths converge on `/api/audio` — Modules 8 → 9 → 11 → 10** (unchanged either way):
```python
story = module8_audio_direction.process(story)            # Story -> Story (+emotion, +direction)
story = module9_audio_production.process(story, tmp_dir)  # Story -> Story (+audio_path, +position_ms)
qa_report = module11_qa_consistency.process(story)         # Story -> QAReport (advisory — see below)
final_path = module10_mixing_timeline.process(story, out)  # Story -> Path (final mp3)
```
Module 11 sits between audio metadata being ready and the final render, exactly where
Architecture.md puts it ("before final render"). It's wrapped in its own try/except in
`app.py` — a QA failure never blocks Module 10 from running; `qa_report` just comes back
`None` in the response if the review pass itself errored.

Verified live end-to-end: `/api/dream` → `/api/audio` through the full 1→2→3→7→8→9→10
chain produces a real playable mp3, not just individually-tested pieces.

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

### `module4_dream_layer_engine/` — Built
- `layers.py` — `generate_layers(graph, session_meta, layer_names=None, model_tier="draft") -> DreamLayers`.
  Not a separate model, per Architecture.md — an orchestration pattern: calls Module 3's
  `NarrativeReconstructionEngine` once per layer (default 4: `conscious_dream`,
  `subconscious_memory`, `hidden_fear`, `symbolic_truth`), each with a different
  `config.layer_persona` string, all against the same `DreamGraph`. Runs in parallel via
  `asyncio.gather` + `asyncio.to_thread` (Module 3's `.reconstruct()` is a sync/blocking
  call, so it needs pushing off the event loop thread to actually run concurrently, not
  serially).
- `_cross_reference_totems` — cross-references Module 2's `is_recurring_symbol` nodes
  against each layer's `provenance_map` so you can show "the red door totem appears in the
  conscious_dream AND hidden_fear layers."
- One bad layer's LLM call failing doesn't take down the others — collected per-layer into
  `DreamLayers.errors`, not raised.
- Endpoint: `POST /api/dream/layers`. Each layer's beats can be fed into Module 7 +
  `/api/audio` independently, exactly like the default single narrative.

### `module6_multi_lens_generation/` — Built
- `lenses.py` — same orchestration pattern as Module 4, using `config.lens_persona`
  instead: one parallel call per lens (default 5: `psychological`, `thriller`, `mystery`,
  `fantasy`, `adventure`).
- Endpoint: `POST /api/dream/lenses`.
- Verified live: two lenses run on the same dream read genuinely differently (thriller
  framed around escalating danger/urgency, fantasy around wonder and impossible imagery)
  in ~15s total for both, confirming they're actually running concurrently, not serially.

### `module5_ripple_regeneration/` — Built
- `ripple.py` — `apply_edit(dream_id, node_id, new_label=None, new_attributes=None)` loads
  the latest persisted graph (Module 2's `db.py`, already versioned by `dream_id`+
  `version`), edits one node, persists it as a NEW version (old version untouched — purely
  additive). `find_affected_beats(previous_narrative, changed_node_ids, changed_node_aliases)`
  is pure Python, no LLM call, using Module 3's own `provenance_map` (`beat_id -> [node_ids]`)
  to find which beats causally depend on the edited node — this is the "diff the graph,
  find affected nodes" step from Architecture.md, and it's free because Module 3 already
  tracked per-beat provenance when it first generated the narrative.
- `regenerate(...)` builds a `RippleContext(previous_output, changed_node_ids)` and calls
  Module 3's engine again — Module 3's own prompt (not duplicated here) instructs the model
  to regenerate only the causally-affected beats and copy the rest through unchanged.
  Re-runs Module 7 on the result so the response's `story` is immediately ready for
  `/api/audio`.
- **Real bug caught and fixed during testing**: Module 3's LLM doesn't reliably put node
  *ids* in a beat's `characters_present` — it sometimes echoes the character's *name*
  instead (confirmed live: a character with id `"1"` and name `"Sam"` showed up as
  `"Sam"` in `characters_present`, not `"1"`). Matching only on id silently reported zero
  affected beats after a rename. Fixed by also matching on the node's pre-edit label
  (`changed_node_aliases`) — re-tested and confirmed 5 of 6 beats correctly flagged
  affected after renaming a character who appears in 5 of the 6 beats.
- Endpoint: `POST /api/dream/edit`. Stateless — the server doesn't persist `NarrativeOutput`
  between requests, so the client sends back its own copy of `narrative_beats` from a prior
  `/api/dream` (or `/api/dream/edit`) call, same pattern `/api/audio` uses for `Story`.

### `module11_qa_consistency/` — Built
- `schemas.py` — `QAIssue` (scene_id, line_index, category, severity, description) and
  `QAReport` (issues + a 0-100 `consistency_score`).
- `reviewer.py` — `review_story(story) -> QAReport`. One OpenAI JSON-mode call over the
  fully-populated Story (every line's `emotion_scores`, `performance_direction`,
  `duration_ms`, and every scene's `sound_cues`) — exactly the "screenplay + generated-
  audio metadata" Architecture.md specifies. Checks exactly two things, per the doc: (1) a
  line's performance direction/emotion contradicting the scene's tone or a character's
  established delivery, (2) dialogue/narration implying a sound (door, footsteps, impact,
  weather) with no matching entry in that scene's `sound_cues`.
- Public API: `process(story) -> QAReport`.
- **Verified it actually detects things**, not just returns a clean report every time: fed
  a hand-built story with a "furious" scene whose line was scripted to speak "very softly
  and calmly" plus two sound-implying lines with zero sound_cues — caught all three
  (the contradiction at `high` severity, both missing-SFX at `medium`), scored 60/100.
  Fed a real, well-formed generated story through the actual pipeline — scored 95/100
  with one genuinely reasonable `low`-severity note, not a false-positive pile-up.
- **Advisory only, by design**: wrapped in its own try/except in `app.py`'s `/api/audio`
  handler, between Module 9 and Module 10. A QA failure (or finding issues at all) never
  blocks the render — `AudioResponse.qa_report` is just `None` if the pass itself errored.

### `module3_narrative_reconstruction/` — Built
- `engine.py` — `NarrativeReconstructionEngine`, the orchestrator: takes a `DreamGraph`,
  builds the prompt, calls the LLM, post-processes into ordered `NarrativeBeat`s.
- `llm_client.py` — thin OpenAI wrapper with a `mock_mode` that auto-activates when
  `OPENAI_API_KEY` isn't set, so this module (and anything downstream) never hard-crashes
  just because billing isn't wired up — returns canned-but-structurally-valid output instead.
- `schemas.py` — pure dataclasses (`NarrativeOutput`, `NarrativeBeat`, `GapFill`,
  `ReconstructionConfig`, etc.); re-exports Module 2's `DreamGraph`/`Node`/`Edge` types
  rather than redefining them, so there's one canonical definition.
- `prompts.py`, `postprocess.py`, `config.py` — prompt construction, contradiction
  detection/provenance mapping, and default model tiers, respectively.
- Public API: `NarrativeReconstructionEngine.input_from_graph(graph, session_meta, config)`
  then `.reconstruct(input) -> NarrativeOutput`.
- Output is prose beats, not the `Story` schema — Module 7 is what converts it into
  something Modules 8-10 can voice.

### `module7_screenplay_conversion/` — Built
- `converter.py` — `convert_to_screenplay(narrative_output, graph, title_hint=None) -> Story`.
  Character list comes straight from the `DreamGraph`'s character nodes (mechanical, no LLM
  needed — the graph already has names/roles). One OpenAI call turns each beat's prose into
  actual dialogue/narration lines + ambient/one-shot sound cues, using the same JSON-mode +
  field-alias-normalization pattern as Module 1's `story_extraction.py`. Falls back to the
  beat's own `characters_present`/first character if the model returns an invalid speaker id.
- Public API: `process(narrative_output, graph, title_hint=None) -> Story`
- This is the module that makes Module 3 not a dead end — without it, reconstructed
  narrative beats had nowhere to go but a JSON response for display.

## Suggested ownership

- **Person A:** `module1_dream_understanding/` — prompt engineering, JSON reliability, story quality
- **Person B:** `module8_audio_direction/` — emotion scoring + performance direction prompt quality
- **Person C:** `module9_audio_production/` — voice casting, prosody mapping, SFX synthesis quality
- **Person D:** `module10_mixing_timeline/` + `app.py` (integration) + `frontend/`
- **Person E:** `module2_dream_graph/` — graph schema, totem-matching quality/threshold tuning, and eventually extending Module 1's schema to extract actual objects/totems (currently the graph only has character/location nodes to match on — see that folder's section above)
- **Person F:** `module3_narrative_reconstruction/` — reconstruction prompt quality, gap-fill confidence tuning
- **Module 7** rides along with whoever owns Module 1 or the `app.py` integration — it's small and its quality depends on the same "does the JSON come back clean" skill as Module 1's extraction prompt
- **Modules 4 and 6** ride along with whoever owns Module 3 — both are thin orchestration layers over the same engine (different persona strings), so their quality is really "how good are the layer/lens persona prompts in `layers.py`/`lenses.py`"
- **Module 5** rides along with whoever owns Module 2 — its correctness depends on graph versioning (Module 2's `db.py`) and provenance data (Module 3's `postprocess.py`) more than on any prompt of its own
- **Module 11** rides along with whoever owns Modules 9/10 (`app.py`'s `/api/audio` handler) — it only makes sense to tune once you're looking at real generated-audio metadata

Whoever owns `app.py` is the integration point — when two modules' contracts need to
change together (e.g. a new `Story` field), that person coordinates the merge.
