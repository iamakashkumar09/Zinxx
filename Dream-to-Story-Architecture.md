# Dream to Story — System Architecture & Model Stack
### (Optimized for a $100 OpenAI API budget)

---

## 1. Problem Recap

**PS:** Dream to Story — user describes a dream or memory, AI turns it into a cinematic audio drama.

Your "Dream Archaeology" framing adds real differentiation on top of the base PS:
- Conversational dream recovery instead of blind auto-completion
- A structured **Dream Graph** (characters, places, objects, emotions, events)
- Multi-layer reality (Inception-style: dream / memory / fear / symbolic truth)
- Ripple-effect regeneration when the user edits a detail
- Multiple narrative lenses (psychological / thriller / fantasy / mystery)
- Final output: a fully produced audio drama (voices + SFX + music + mix)

The rest of this doc maps each of those pieces to a concrete pipeline stage and a concrete model, with OpenAI as the primary engine (since that's where your $100 lives) and free/open fallbacks called out wherever OpenAI has no product for that modality.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ 0. CAPTURE            User types or speaks their dream               │
├─────────────────────────────────────────────────────────────────────┤
│ 1. DREAM UNDERSTANDING  →  extract entities, gaps, contradictions    │
├─────────────────────────────────────────────────────────────────────┤
│ 2. CONVERSATIONAL RECOVERY  →  LLM asks targeted follow-up questions │
├─────────────────────────────────────────────────────────────────────┤
│ 3. DREAM GRAPH BUILD  →  structured graph (nodes + edges) in DB      │
├─────────────────────────────────────────────────────────────────────┤
│ 4. NARRATIVE RECONSTRUCTION  →  fills gaps, preserves dream logic    │
├─────────────────────────────────────────────────────────────────────┤
│ 5. DREAM LAYER ENGINE  →  splits story into reality layers + totems  │
├─────────────────────────────────────────────────────────────────────┤
│ 6. LENS SELECTION  →  psychological / thriller / mystery / fantasy   │
├─────────────────────────────────────────────────────────────────────┤
│ 7. SCREENPLAY CONVERSION  →  scenes, dialogue, narration, cues       │
├─────────────────────────────────────────────────────────────────────┤
│ 8. AUDIO DIRECTION ENGINE  →  voice casting, emotion, SFX/music plan │
├─────────────────────────────────────────────────────────────────────┤
│ 9. AUDIO PRODUCTION  →  TTS + ambience + foley + music generation    │
├─────────────────────────────────────────────────────────────────────┤
│ 10. MIXING & TIMELINE  →  ducking, reverb, transitions, normalize    │
├─────────────────────────────────────────────────────────────────────┤
│ 11. QA / CONSISTENCY  →  voice/emotion/story coherence checks        │
└─────────────────────────────────────────────────────────────────────┘
        ↑ interactive edit at any node → ripple-regenerate downstream
```

Stages 0–7 are almost pure LLM/text work (cheap). Stages 8–10 are where the money and the engineering complexity go — plan your $100 accordingly (see §5).

---

## 3. Module-by-Module Model Choices

### Module 1 — Dream Understanding & Conversational Recovery
**Job:** parse the raw dream text, extract entities/emotions/scene breaks, detect what's missing or contradictory, and ask 1–3 natural follow-up questions ("You said you were in a house — was it a house you recognize?").

- **Model:** `gpt-5.4-mini` (or `gpt-4.1-mini` if you want a cheaper fallback) with **Structured Outputs** (strict JSON schema) for the extraction pass, and free-form chat for the question-generation pass.
- Why mini here: this runs multiple times per session (every user reply triggers re-extraction), so keep it cheap. Reserve full `gpt-5.4`/`gpt-5.5` for the creative writing stages where quality matters more than speed.
- Optional voice input: `gpt-4o-mini-transcribe` (~$0.003/min) to let users *speak* their dream instead of typing it — a nice demo moment.

### Module 2 — Dream Graph
**Job:** persistent structured representation: `Character`, `Location`, `Object/Totem`, `Emotion`, `Event`, `Transition`, with typed edges (`feels`, `owns`, `transforms_into`, `happens_before`).

- Not a model — this is a **schema + database** decision. Use Structured Outputs to force the LLM to emit graph-shaped JSON every turn; store in Postgres (with a JSON column) or a lightweight graph DB (Neo4j free tier, or just adjacency tables in Postgres — simpler for a hackathon).
- **Embeddings:** `text-embedding-3-small` (~$0.02/1M tokens) to embed characters/symbols/totems so the system can recognize "this dream's totem is the same red door from three sessions ago" via similarity search. Store in a small vector store (pgvector, Chroma, or FAISS — all free/self-hosted).

### Module 3 — Narrative Reconstruction Engine
**Job:** fill narrative gaps while preserving surreal dream logic; this is the main creative-writing LLM call.

- **Model:** `gpt-5.4` for the actual scene generation (quality matters — this is what gets voiced). Use `gpt-5.4-mini` for cheaper draft passes during testing/iteration, then switch to the full model for your final demo run.
- Feed it the Dream Graph as structured context (RAG-style — don't dump the whole conversation history every call, just the graph + last few turns, per your own earlier notes on layered memory).

### Module 4 — Dream Layer Engine (Inception-style)
**Job:** organize the reconstructed narrative across layers (conscious dream / subconscious memory / hidden fear / symbolic truth) and place recurring totems across layers.

- Not a separate model — an **orchestration pattern**: run the Module 3 model multiple times with different system prompts, each conditioned on "you are writing the [layer name] layer of this dream, using the same Dream Graph but surfacing [subconscious drivers / literal events / symbolic distortions]." Cross-reference layers through the Dream Graph's totem nodes so the same object recurs meaningfully.
- This is genuinely your most defensible "innovation" surface for a judging panel — it's pure prompt/graph engineering, so it costs almost nothing in API credits, which is good news for your budget.

### Module 5 — Interactive Ripple Regeneration
**Job:** when a user changes a decision or recalls a new detail mid-story, regenerate everything downstream without breaking consistency.

- Version the Dream Graph (simple: store graph snapshots keyed by edit event). On edit, diff the graph, identify which narrative/audio nodes depend on the changed node (via edges), and only re-run Modules 3–9 for the **affected subtree** — not the whole story. This is what keeps your OpenAI bill sane when users experiment with edits.

### Module 6 — Multi-Lens Narrative Generation
**Job:** same dream, told through psychological / thriller / mystery / fantasy / adventure lenses.

- **Model:** `gpt-5.4-mini`, one call per lens, same Dream Graph input, different system-prompt persona ("You are a psychological-thriller screenwriter..."). Run these in parallel (async) — they're independent, so no reason to serialize them.

### Module 7 — Screenplay Conversion
**Job:** turn the finalized narrative into a structured screenplay: scene headers, narration, dialogue lines tagged by character, SFX cues, music cues, pacing notes.

- **Model:** `gpt-5.4` with Structured Outputs, schema roughly:
```json
{
  "scenes": [{
    "location": "", "layer": "",
    "lines": [{"speaker": "", "text": "", "emotion": "", "delivery_notes": ""}],
    "sfx_cues": [{"trigger_line_id": "", "sound": ""}],
    "music_cue": {"mood": "", "intensity": 0-10},
    "ambience": ""
  }]
}
```
This structured screenplay is the contract between your text pipeline and your audio pipeline — everything downstream just reads this object.

### Module 8 — Audio Direction Engine (your stated "innovation" layer)
**Job:** decide *how* each line should sound — voice casting, emotional delivery parameters, ambience, foley, music, timing — before any audio is generated.

- **Model:** `gpt-5.4-mini` is plenty here — it's a planning/reasoning task over already-structured screenplay data, not open-ended prose generation. Output feeds directly into the TTS `instructions` field and into your sound-effect prompt list.
- Example instruction it should produce per line: `"Speak slowly, hushed, slightly trembling, long pause before the last word."` — this is exactly the kind of natural-language steering `gpt-4o-mini-tts` accepts.

### Module 9 — Audio Production

| Sub-task | Recommended model | Notes |
|---|---|---|
| Character voices (emotion-aware TTS) | **`gpt-4o-mini-tts`** | Steerable via natural-language `instructions` param (tone, pace, emotion, whisper, pauses). ~13 voices, ~$0.015/min of audio. This is your primary TTS engine — cheap and directly prompt-controllable, which matches your Audio Direction Engine's output. |
| Higher-fidelity narrator voice (optional, for your best/demo scenes) | `tts-1-hd` | Better fidelity, no steerability — use only for a small number of showcase lines if budget allows. |
| Speech-to-text (if voice input) | `gpt-4o-mini-transcribe` or `whisper-1` | Cheap, reliable. |
| Storyboard / key-art stills for the "screenplay" or app UI | `gpt-image-1-mini` | ~$0.005–0.01/image — good enough for concept art / demo visuals without denting your budget. Use `gpt-image-2` sparingly only for your single best hero image if you want top quality for the pitch. |
| **Ambience / Foley / SFX** | **OpenAI has no product for this** — do not budget OpenAI credits here. | Use a free, self-hosted open-source model: **Stable Audio Open** (best local option, GPU required) or **AudioGen** (Meta AudioCraft) for environmental sound/foley. If GPU access is limited, build a small **pre-recorded SFX library** (freesound.org, CC0) and have the Audio Direction Engine pick from it by tag-matching — much cheaper and totally viable for a hackathon demo. |
| **Background music** | Same as above — not an OpenAI capability. | Use a royalty-free music library (Pixabay Music, YouTube Audio Library) tagged by mood/intensity and selected by the Audio Direction Engine, or self-hosted MusicGen if you have GPU time. |

**Bottom line on your $100:** spend it almost entirely on `gpt-5.4`/`gpt-5.4-mini` (text) and `gpt-4o-mini-tts` (voices). Sound effects and music should come from free libraries or self-hosted open models — OpenAI simply doesn't sell that modality, and trying to force it in isn't worth the engineering time in a hackathon window.

### Module 10 — Mixing & Timeline Composition
**Job:** dialogue ducking under music, reverb per-layer (e.g. echo for the "symbolic truth" layer), scene-transition fades, loudness normalization.

- Not an AI task — this is DSP/audio engineering. Use `pydub` + `ffmpeg` (both free) for ducking, crossfades, and normalization; a simple rule-based mixer (e.g. auto-lower music -12dB whenever a dialogue track is active) gets you 90% of the perceived quality for near-zero cost.

### Module 11 — Quality/Consistency Review
**Job:** catch a character whose voice/emotion contradicts earlier scenes, or a "door opened" line with no door SFX.

- **Model:** one cheap `gpt-5.4-mini` pass over the finished screenplay + generated-audio metadata (durations, cue list) before final render. This is a text-only reasoning task, so it's nearly free relative to the audio generation cost.

---

## 4. Concrete OpenAI Model Roster (as of mid-2026)

| Model | Role in your pipeline | Approx. cost |
|---|---|---|
| `gpt-5.4` | Final narrative writing, screenplay conversion, final QA of hero scenes | Standard tier — reserve for final/demo runs |
| `gpt-5.4-mini` | Extraction, follow-up questions, lens variants, audio direction planning, draft iteration | Half the cost of `gpt-5.4` — use for all dev/testing |
| `gpt-4.1-nano` | Trivial classification tasks (e.g. "is this scene a transition?") if you want to shave cost further | Cheapest text model available |
| `text-embedding-3-small` | Totem/character/symbol memory, semantic search over the Dream Graph | ~$0.02/1M tokens — negligible |
| `gpt-4o-mini-tts` | Primary character/narrator voices, steerable by natural-language emotion instructions | ~$0.60/1M input tokens + $12/1M audio-output tokens (~$0.015/min) |
| `tts-1-hd` | A handful of showcase-quality lines only | ~$30/1M characters |
| `gpt-4o-mini-transcribe` | Voice-in dream capture (optional) | ~$0.003/min |
| `gpt-image-1-mini` | Concept art / storyboard stills for the demo | ~$0.005–0.01/image |

Everything else (ambience, foley, music, mixing) sits outside OpenAI's product line — see Module 9 table above for the free alternatives.

---

## 5. Spending the $100 Sensibly

A rough budget split for a hackathon build cycle:

- **~$20 — development & iteration:** hundreds of test calls to `gpt-5.4-mini` while you tune prompts and the Dream Graph schema. Text tokens are cheap; this line item is mostly a safety margin.
- **~$50 — TTS generation:** at ~$0.015/min with `gpt-4o-mini-tts`, that's over 3,000 minutes of generated speech across all your test dreams and demo runs — more than enough even with heavy re-generation during ripple-effect testing.
- **~$15 — final polish:** a `gpt-5.4` full pass on your best demo dream, plus a few `tts-1-hd` lines and a couple of `gpt-image-1-mini`/`gpt-image-2` concept images for the pitch deck.
- **~$15 — buffer:** rate-limit retries, judge live-demo runs, last-minute fixes.

**Practical rule:** develop and test everything on the `-mini` tier. Only swap in the full `gpt-5.4` + `tts-1-hd` combo for the 2–3 dream stories you'll actually show the judges.

---

## 6. Suggested Tech Stack (non-AI parts)

- **Backend:** FastAPI (async, plays well with streaming LLM/TTS calls)
- **DB:** Postgres (Dream Graph as JSON/relational hybrid) + pgvector for embeddings — avoids running a separate vector DB service
- **Task queue:** Celery or even just `asyncio` background tasks for a hackathon scope — don't over-engineer this
- **Audio assembly:** `pydub` + `ffmpeg`
- **Frontend:** whatever you're fastest in — the interesting engineering is entirely on the backend/pipeline side

---

## 7. What to Build First (priority order for limited hackathon time)

1. Dream capture → extraction → follow-up Q&A loop (Modules 1–2) — this is your core UX hook, get it feeling magical first.
2. Dream Graph → single-layer narrative reconstruction (Module 3) — prove the "fills gaps while preserving dream logic" claim with real output.
3. Screenplay conversion + Audio Direction Engine (Modules 7–8) — the structured contract that unlocks everything downstream.
4. TTS production with `gpt-4o-mini-tts` (Module 9, voices only) — get one full dream *audibly* narrated end-to-end before adding SFX/music.
5. Basic mixing (dialogue + one ambience bed + simple ducking) — even a single looping rain/forest bed under narration reads as "cinematic" to a judge.
6. Only then: multi-layer Dream Layer Engine, multi-lens generation, ripple-effect editing, and richer foley — these are impressive but not load-bearing for a working demo, and each adds real engineering time.

Get steps 1–5 rock solid first. Steps 6 are what differentiate you from other teams *if you have time left* — don't let them block a working end-to-end demo.
