# Dream to Story — PPT / Presentation Content

Everything needed to build the deck: problem statement, architecture, tech stack per module,
data flow, a worked example, and the engineering story (what broke, what we fixed). Organized
so each `##` section can become one or more slides.

---

## 1. Problem Statement

**PS:** Dream to Story — a user describes a dream or memory in free text (or speaks it), and
the system turns it into a fully-produced **cinematic audio drama**: multiple character
voices, emotional vocal delivery, ambient sound design, sound effects, background music, and
a final mixed track — automatically.

### Our differentiator: "Dream Archaeology"

Instead of one-shot text-to-audio, we treat the dream as something to be *excavated and
reconstructed*, not just transcribed:

- **Structured memory** — every dream is parsed into a graph (characters, places, objects,
  emotions, events), not just a paragraph.
- **Gap-filling that preserves dream logic** — surreal, illogical elements are treated as
  features to keep, not bugs to "fix" into realism.
- **Multi-layer reality** (Inception-style) — the same dream can be retold as the literal
  event, the subconscious memory underneath it, the hidden fear it's about, or its symbolic
  meaning.
- **Ripple-effect editing** — change one detail, and only the parts of the story that actually
  depend on it regenerate, not the whole thing.
- **Multiple narrative lenses** — the same dream retold as psychological drama, thriller,
  mystery, fantasy, or adventure.
- **Recurring symbol / totem memory** — the system recognizes when the same object or figure
  ("the red door," "my old friend Maya") reappears across a person's dreams over time.

---

## 2. High-Level Architecture (11 Modules)

```
 0. CAPTURE                 User types or speaks their dream
 │
 1. DREAM UNDERSTANDING     → extract characters, scenes, dialogue, sound cues
 2. DREAM GRAPH             → structured graph (nodes + edges), persisted, totem memory
 3. NARRATIVE RECONSTRUCTION→ fills gaps, preserves dream logic, writes real prose
 4. DREAM LAYER ENGINE      → same dream retold across 4 reality layers   (on-demand)
 5. RIPPLE REGENERATION     → edit a detail → only affected beats regenerate (on-demand)
 6. MULTI-LENS GENERATION   → same dream retold across 5 genres           (on-demand)
 7. SCREENPLAY CONVERSION   → narrative prose → scenes, dialogue lines, sound cues
 8. AUDIO DIRECTION         → per-line emotion scoring + vocal performance notes
 9. AUDIO PRODUCTION        → TTS voices + procedurally synthesized SFX/ambience/music
10. MIXING & TIMELINE       → duck, layer, crossfade, normalize → final mp3
11. QA / CONSISTENCY        → self-review pass, catches contradictions, scores the result
 │
 ▼
 Final playable, downloadable audio drama
```

Modules 4/5/6 are **on-demand extras** layered on top of the same Module 3 engine — they are
not required for the default one-shot generation flow, they're additional interactive
features (see §5).

---

## 3. Tech Stack — Model/Tool Used, Per Module

| # | Module | What it does | Tech / Model used |
|---|---|---|---|
| 1 | Dream Understanding | Raw text → structured story (characters, scenes, dialogue, sound cues) | **OpenAI `gpt-4o`**, JSON mode |
| — | *(voice input, optional)* | Spoken dream → text | **Groq — `whisper-large-v3-turbo`** (free tier) |
| 2 | Dream Graph | Story → typed node/edge graph; persists it; detects recurring symbols | Plain Python + **SQLite** (`aiosqlite`); **OpenAI `text-embedding-3-small`** for totem similarity search |
| 3 | Narrative Reconstruction | Graph → reconstructed prose, gap-filled, dream-logic preserved | **OpenAI `gpt-5.4-mini`** (draft) / **`gpt-5.4`** (final tier) |
| 4 | Dream Layer Engine | Same graph → 4 parallel reality-layer retellings | Orchestration only — re-runs Module 3's engine with different personas, `asyncio.gather` |
| 5 | Ripple Regeneration | Graph edit → diff → regenerate only affected narrative beats | Pure Python graph diffing (`provenance_map`) + Module 3's engine on the affected subtree only |
| 6 | Multi-Lens Generation | Same graph → 5 parallel genre retellings | Orchestration only — same pattern as Module 4, different personas |
| 7 | Screenplay Conversion | Narrative prose → structured scenes (dialogue lines + sound cues) | **OpenAI `gpt-4o`**; characters pulled directly from the graph (not re-generated) |
| 8 | Audio Direction | Score each line's emotion; write a vocal performance instruction | **HuggingFace `j-hartmann/emotion-english-distilroberta-base`** (local, free, runs on CPU) + **OpenAI `gpt-4o`** |
| 9 | Audio Production | Generate voices, sound effects, ambience, background music | **edge-tts** (free Microsoft neural TTS, 8-voice pool) for dialogue; **procedural DSP synthesis** (`numpy` + `scipy`) for every sound effect, ambience bed, and music cue — zero external audio API |
| 10 | Mixing & Timeline | Layer everything into one track: duck, crossfade, normalize | **`pydub` + `ffmpeg`** — pure audio engineering, no AI |
| 11 | QA / Consistency | Re-review the finished script, score it, flag contradictions | **OpenAI `gpt-4o`**, advisory-only (never blocks output) |

### Why this stack (vs. the original spec's paid-API assumptions)

The original architecture doc assumed OpenAI's `gpt-4o-mini-tts` for voices and paid/GPU
models (Stable Audio Open, AudioGen) for sound effects and music. We deliberately swapped
those two pieces for **free, local, offline-capable alternatives** (edge-tts + procedural
numpy/scipy synthesis) — this keeps the entire audio-production layer at zero marginal cost
per generation, with no external dependency beyond the text-generation calls. Everything else
(text understanding, reconstruction, screenplay, direction, QA) stayed on OpenAI as the
original spec intended, since that's where quality genuinely matters most.

---

## 4. Full Tech Stack Summary

| Layer | Technology |
|---|---|
| Backend framework | **FastAPI** (Python, async) |
| Frontend | Vanilla HTML/CSS/JS (no framework/build step) |
| Database | **SQLite** (`aiosqlite`) — Dream Graph persistence |
| LLM (text generation) | **OpenAI** — `gpt-4o` (extraction/screenplay/direction/QA), `gpt-5.4-mini`/`gpt-5.4` (narrative reconstruction) |
| Embeddings | **OpenAI `text-embedding-3-small`** — recurring symbol/totem memory |
| Speech-to-text | **Groq** — `whisper-large-v3-turbo` (voice input only) |
| Text-to-speech | **edge-tts** — free Microsoft neural voices, 8-voice pool, per-character consistency |
| Emotion classification | **HuggingFace Transformers** — `j-hartmann/emotion-english-distilroberta-base`, local inference |
| Sound design (SFX/ambience/music) | **Procedural synthesis** — `numpy` + `scipy`, custom DSP (noise shaping, pitch-swept tones, envelopes, mood-driven filtering) |
| Audio mixing | **`pydub` + `ffmpeg`** |
| E2E testing | **Playwright** (dev-time verification, not runtime) |

---

## 5. Data Flow / API Surface

Two entry points into the text pipeline, both converging on one audio pipeline:

```
/api/story   (fast preview)
    Module 1 only → Story in ~2-5s, shown immediately while the rest works

/api/dream   (full "dream archaeology" pipeline — what the UI actually uses)
    Module 1 → Module 2 → Module 3 → Module 7 → Story + narrative beats + gap-fill count

/api/audio   (both paths converge here)
    Module 8 → Module 9 → Module 11 (advisory) → Module 10 → final mp3 + QA report

/api/dream/layers    Module 4 → 4 parallel reality-layer retellings
/api/dream/lenses    Module 6 → 5 parallel genre retellings
/api/dream/edit      Module 5 → ripple-regenerate only the affected narrative beats
/api/transcribe      Voice input → text (Groq Whisper)
```

---

## 6. Worked End-to-End Example

**Input (typed or spoken):**
> "I was walking through my old school hallway. I saw my friend Maya standing by the lockers.
> A bell rang loudly and the lights flickered."

| Step | Module | What happens |
|---|---|---|
| 1 | Dream Understanding | `gpt-4o` extracts: characters (Narrator, Maya), one scene ("school hallway," nostalgic tone), dialogue lines, sound cues (bell, flickering lights) |
| 2 | Dream Graph | Facts become a graph: *Maya —appears in→ hallway scene*, *hallway —feels→ nostalgic*. Saved to SQLite. `text-embedding-3-small` embeds "Maya" / "school hallway" for future cross-dream recognition |
| 3 | Narrative Reconstruction | `gpt-5.4-mini` rewrites the graph into real prose: *"I walked down the old hallway, footsteps echoing, when I spotted Maya by the lockers. Then the bell rang out, sharp and sudden, and the lights flickered overhead."* |
| 7 | Screenplay Conversion | `gpt-4o` splits that into an actual script: who says which line, plus a clean sound-cue list (bell ring, light flicker/buzz, footsteps) |
| 8 | Audio Direction | Local HF model scores each line's emotion (mostly joy/nostalgia); `gpt-4o` writes: *"Warm, wistful tone, slightly slower pace, like remembering something fondly."* |
| 9 | Audio Production | edge-tts speaks the lines with that emotional coloring (rate/pitch nudged accordingly); numpy/scipy synthesizes the bell ring and light-flicker buzz from scratch; a soft mood-matched background chord pad is generated |
| 10 | Mixing | `pydub`/`ffmpeg` layers voice (front) + ambience/music (quieter, underneath) + one-shot SFX (at their exact timestamps), crossfades scenes, normalizes loudness, exports one mp3 |
| 11 | QA Review | `gpt-4o` re-reads the finished script + cue list, scores it 0–100, flags anything that doesn't add up (e.g. a mentioned sound with no matching cue) |

**Output:** one downloadable, fully mixed audio drama — narrated dialogue, a bell, flickering
lights, and mood-appropriate background music, all generated automatically from three
sentences of free text.

---

## 7. Engineering Depth — Real Problems Found & Solved

Good talking points for judges: this wasn't just "call an LLM and mix the output" — a lot of
non-obvious pipeline-integrity bugs surfaced under real testing and were fixed with targeted,
verifiable engineering (spectral analysis, live end-to-end tracing, not guesswork):

- **Information loss across pipeline stages** — the Dream Graph originally only carried a
  scene's *setting label* forward, not its actual dialogue/sound content, so the Narrative
  Reconstruction stage had almost nothing concrete to work from and invented vague prose.
  Fixed by enriching graph nodes with the real underlying content.
- **LLM instruction-following isn't guaranteed, so don't rely on it alone** — added a
  *mechanical* sound-cue completeness check in Screenplay Conversion that cross-checks every
  originally-described sound against the final script and backfills anything missing,
  independent of what the narrative prose says.
- **Voice identity vs. emotional expressiveness trade-off** — large pitch swings made the same
  character sound like a different speaker between lines; rebalanced so *rate* (pace) carries
  most of the emotional signal and *pitch* stays a light seasoning, preserving both
  recognizability and expressiveness.
- **Background music was nearly inaudible** — an early mix had ~45% of the music's energy in
  near-inaudible sub-bass; rebalanced the chord layering and gain staging so mood-driven music
  is actually present in the final mix.
- **Ambient vs. one-shot sound classification gap** — the LLM can classify the same sound
  ("a bell ringing," "a dog barking") as either a one-shot event or a continuous ambience —
  but the ambience-synthesis path had no dedicated handling for animal/bell sounds and fell
  back to generic filtered noise. Fixed by giving every sound category a proper generator on
  *both* paths, verified with real spectral (FFT) analysis, not just listening.
- **Merged-cue sound loss** — when the LLM described two sounds in one cue ("a dog barking,
  answered by a wolf"), only the first-matching sound generator fired, silently dropping the
  second. Fixed to layer every distinct sound named in a cue.
- **Simultaneous cue stacking** — multiple sound cues anchored to the same line ("before
  line 1") all resolved to the identical millisecond and piled up into one indistinct burst.
  Fixed by staggering same-anchor cues.

---

## 8. Suggested Slide Breakdown

1. Title + problem statement
2. "Dream Archaeology" — our differentiator (bullet list from §1)
3. High-level architecture diagram (§2)
4. Tech stack table (§3 or the condensed §4)
5. Data flow diagram (§5)
6. Worked example walkthrough (§6) — great for a live-feeling demo slide
7. Engineering depth / what we debugged (§7) — strong for judge Q&A credibility
8. Live demo / closing
