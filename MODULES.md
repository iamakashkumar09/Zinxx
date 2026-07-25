# Module Map

The folder structure under `modules/` mirrors `Dream-to-Story-Architecture.md`'s 11 modules
exactly, one folder per module, numbered to match. This file is the integration contract:
what's built, what talks to what, and where to plug in what isn't built yet.

## Status at a glance

| # | Folder | Architecture.md module | Status |
|---|---|---|---|
| 1 | `module1_dream_understanding/` | Dream Understanding & Conversational Recovery | **Built** (Groq) |
| 2 | `module2_dream_graph/` | Dream Graph | Stub — not implemented |
| 3 | `module3_narrative_reconstruction/` | Narrative Reconstruction Engine | Stub — folded into Module 1 |
| 4 | `module4_dream_layer_engine/` | Dream Layer Engine (Inception-style) | Stub — not implemented |
| 5 | `module5_ripple_regeneration/` | Interactive Ripple Regeneration | Stub — not implemented |
| 6 | `module6_multi_lens_generation/` | Multi-Lens Narrative Generation | Stub — not implemented |
| 7 | `module7_screenplay_conversion/` | Screenplay Conversion | Stub — folded into Module 1 |
| 8 | `module8_audio_direction/` | Audio Direction Engine | **Built** (Groq + local HF classifier) |
| 9 | `module9_audio_production/` | Audio Production | **Built** (edge-tts + procedural SFX) |
| 10 | `module10_mixing_timeline/` | Mixing & Timeline Composition | **Built** (pydub) |
| 11 | `module11_qa_consistency/` | Quality/Consistency Review | Stub — not implemented |

Every stub folder's `__init__.py` explains, in its own docstring, why it's skipped and
where it would plug into the pipeline if someone picks it up.

## Runtime pipeline (what actually runs on every request)

Only Modules 1, 8, 9, 10 run today. Each one's output is literally the next one's input —
see `app.py`, which is the one file where all 4 meet:

```python
story = module1_dream_understanding.process(text)        # text -> Story
story = module8_audio_direction.process(story)            # Story -> Story (+emotion, +direction)
story = module9_audio_production.process(story, tmp_dir)  # Story -> Story (+audio_path, +position_ms)
final_path = module10_mixing_timeline.process(story, out) # Story -> Path (final mp3)
```

We use **Groq** (Llama 3.3 70B) instead of the architecture doc's OpenAI models, and
**edge-tts** + **procedural numpy/scipy synthesis** instead of `gpt-4o-mini-tts` +
Stable Audio Open/AudioGen — same module boundaries, free-tier stack.

## The shared contract: `shared/models.py`

The `Story` object (and its nested `Character`, `Scene`, `Line`, `SoundCue`) is the only
thing that crosses module boundaries. If you're changing a field name or type in here,
tell the other 3 people first — every module reads and writes this same object.

- Module 1 **creates** `Story` (title, characters, scenes, lines, sound_cues — `prompt`/`position` set, everything else `None`)
- Module 8 **fills in** `Line.emotion_scores` + `Line.performance_direction`
- Module 9 **fills in** `Line.audio_path` + `Line.duration_ms`, and `SoundCue.position_ms`
- Module 10 **reads** the fully-populated `Story` and produces the final audio file (doesn't mutate `Story` further)

Other shared code (not module-specific, anyone can use):
- `shared/config.py` — env vars + mixing constants (`GROQ_API_KEY`, `LINE_GAP_MS`, gain levels, etc.)
- `shared/llm_client.py` — the Groq client factory, used by both Module 1 and Module 8

## Folder-by-folder

### `module1_dream_understanding/` — Built
- `story_extraction.py` — the Groq call + prompt. Public API: `process(raw_text) -> Story`
- Also does Architecture.md Modules 3 (Narrative Reconstruction) and 7 (Screenplay
  Conversion) inline, in the same prompt/call — there's no separate Dream Graph to feed a
  multi-step version of this.

### `module8_audio_direction/` — Built
- `emotion_scoring.py` — local HuggingFace classifier (`j-hartmann/emotion-english-distilroberta-base`), no API
- `performance_direction.py` — Groq call, one per scene, batches all lines in that scene
- Public API: `process(story) -> Story`

### `module9_audio_production/` — Built
- `voice_generation.py` — edge-tts, one consistent voice per character, prosody driven by Module 8's emotion scores
- `sound_cues.py` — resolves "before/after line N" hints into millisecond offsets using real TTS durations
- `sfx_synth.py` — procedural ambience + one-shot SFX (numpy/scipy noise shaping, no samples/API)
- Public API: `process(story, tmp_dir) -> Story`

### `module10_mixing_timeline/` — Built
- `mixing.py` — pydub: per-scene dialogue + ambience underlay + one-shot overlay, scene concat with crossfade, normalize, export mp3
- Public API: `process(story, output_dir) -> Path`

### `module2_dream_graph/`, `module4_dream_layer_engine/`, `module5_ripple_regeneration/`, `module6_multi_lens_generation/`, `module11_qa_consistency/` — Stubs
Each has a docstring explaining the intended design per Architecture.md and what it would
depend on. `module6_multi_lens_generation` is the easiest one to pick up first (no
dependency on the others); `module4_dream_layer_engine` is the architecture doc's own pick
for highest-value "if you have time left" feature, but needs Module 2 first.

### `module3_narrative_reconstruction/`, `module7_screenplay_conversion/` — Stubs (folded into Module 1)
These exist as folders for structural completeness but their logic currently lives inside
Module 1's single prompt. Splitting them out only makes sense once Module 2 (Dream Graph)
exists to feed a real multi-step version.

## Suggested ownership (4 people)

- **Person A:** `module1_dream_understanding/` — prompt engineering, JSON reliability, story quality
- **Person B:** `module8_audio_direction/` — emotion scoring + performance direction prompt quality
- **Person C:** `module9_audio_production/` — voice casting, prosody mapping, SFX synthesis quality
- **Person D:** `module10_mixing_timeline/` + `app.py` (integration) + `frontend/`

Whoever owns `app.py` is the integration point — when two modules' contracts need to
change together (e.g. a new `Story` field), that person coordinates the merge.
