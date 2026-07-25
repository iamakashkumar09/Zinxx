# Module 3 — Narrative Reconstruction Engine

Part of the **Dream to Story** pipeline. This module owns exactly one job:

> Take a structured Dream Graph (Module 2) + recent conversation context, and produce a
> gap-filled, dream-logic-preserving narrative — **without** touching layers (Module 4),
> lenses (Module 6), screenplay formatting (Module 7), or audio (Modules 8–10).

Keeping it single-purpose is what makes it swappable/debuggable in isolation.

---

## 1. Where this sits in the bigger system

```
Module 1 (Understanding)  ─┐
Module 2 (Dream Graph)    ─┼──►  MODULE 3: Narrative Reconstruction  ──►  Module 4 (Layers)
                            │         ▲                                  Module 5 (Ripple)
                            │         │ re-run on edit (Module 5)        Module 6 (Lenses)
                            └─────────┘                                  Module 7 (Screenplay)
```

- **Upstream dependency:** Module 2's Dream Graph is the *only* required structured input.
  Module 3 never talks to the raw conversation transcript directly — it gets a trimmed
  window of recent turns, RAG-style, per the architecture doc's memory rule.
- **Downstream consumers:** Module 4 runs this engine multiple times (once per reality
  layer) with different system-prompt personas. Module 6 runs it once per lens. Both
  reuse this same engine — they don't reimplement reconstruction logic.
- **Module 5 (Ripple Regeneration)** calls this module again after a graph edit, passing
  `previous_output` + a diff, so the engine can do a cheaper *partial* regeneration
  instead of starting from scratch.

Because 3 other modules call into this one, its I/O contract has to be stable and boring.

---

## 2. Input contract

```
ReconstructionInput
├── dream_graph            (required) DreamGraph — nodes + typed edges from Module 2
├── conversation_context    (optional) list[ConversationTurn] — last N turns only
├── session_meta            (required) SessionMeta — ids, language, timestamp
├── config                  (optional) ReconstructionConfig
│     ├── model_tier: "draft" | "final"
│     ├── preserve_dream_logic: bool           (default True)
│     ├── target_length: "short"|"medium"|"long"
│     ├── layer_persona: str | None            (set by Module 4, not used directly here)
│     └── lens_persona: str | None             (set by Module 6, not used directly here)
└── previous_output         (optional) NarrativeOutput | None — for ripple regeneration
      + changed_node_ids: list[str]            (which graph nodes triggered the re-run)
```

`layer_persona` / `lens_persona` are plain strings the *caller* (Module 4 or 6) injects
into the system prompt. Module 3 doesn't know what a "layer" or "lens" is — it just
takes an optional persona string. This is what keeps it reusable instead of forking.

## 3. Output contract

```
NarrativeOutput
├── narrative_id
├── beats: list[NarrativeBeat]
│     ├── beat_id, order
│     ├── location_ref, characters_present   (graph node ids — the provenance link)
│     ├── narrative_text                     (the actual prose)
│     ├── dream_logic_elements               (surreal bits deliberately kept, not "fixed")
│     ├── gap_fills: list[GapFill]           (what was invented + confidence + why)
│     └── emotional_tone
├── graph_updates: list[GraphUpdate]          (new nodes/edges implied by the reconstruction,
│                                               to be written back into Module 2's store)
├── provenance_map: dict[beat_id -> [graph_node_ids]]   (used by Module 11 QA + Module 5 diffing)
├── warnings: list[str]                       (low-confidence fills, unresolved contradictions)
└── generation_metadata: model, tokens, latency, timestamp
```

This is the *only* object Modules 4, 6, 7 and 11 are allowed to depend on. If the
internals of this module change, as long as `NarrativeOutput`'s shape doesn't, nothing
downstream breaks.

---

## 4. Internal pipeline (inside `reconstruct()`)

```
1. trim_graph(dream_graph)              → cap nodes/edges to keep prompt small
2. trim_context(conversation_context)   → last MAX_CONTEXT_TURNS only
3. build_system_prompt(...)             → persona + dream-logic rules + optional layer/lens persona
4. build_user_prompt(...)               → graph as JSON + context + regen diff if present
5. llm_client.generate(...)             → structured-output call, JSON-schema enforced
6. parse_llm_output(raw_json)           → NarrativeOutput (unvalidated)
7. postprocess.detect_contradictions()  → cross-check totems/characters vs graph
8. postprocess.extract_graph_updates()  → find new entities the LLM introduced
9. postprocess.build_provenance_map()   → link every beat back to graph node ids
10. return NarrativeOutput
```

Steps 7–9 are pure Python (no extra LLM call) so a partial-regeneration ripple run stays
cheap — only step 5 costs money.

---

## 5. Files

| File | Responsibility |
|---|---|
| `config.py` | Model names, temperature, token caps, context window size. Change models here only. |
| `schemas.py` | All dataclasses for input/output. No logic — just shape + (de)serialization. |
| `prompts.py` | Builds the system + user prompt strings. Pure functions, easy to unit test/print. |
| `llm_client.py` | Thin OpenAI wrapper. Has a `mock_mode` so the rest of the module runs with no API key. |
| `postprocess.py` | Contradiction detection, graph-update extraction, provenance mapping. No LLM calls. |
| `engine.py` | `NarrativeReconstructionEngine` — orchestrates the 10 steps above. This is the public API. |
| `example_usage.py` | Runnable demo with a mock Dream Graph, `mock_mode=True`. |

## 6. Swapping in a real API key

`llm_client.py` reads `OPENAI_API_KEY` from the environment. With no key set, or with
`NarrativeLLMClient(mock_mode=True)`, it returns a deterministic canned response so you
can develop/debug Modules 4–11 without spending anything. Flip `mock_mode=False` (and
export the key) when you're ready to hit the real model.

## 7. Debugging notes

- Every LLM call's raw prompt + raw response is returned in `generation_metadata.debug`
  when `config.debug=True` — turn this on first when something looks wrong.
- `postprocess.detect_contradictions` never raises; it only appends to `warnings`. The
  engine should never crash on messy LLM output — surface problems, don't halt the
  pipeline.
- If `graph_updates` looks empty on every run, check that the LLM is actually being
  told (in `prompts.py`) that inventing named entities is allowed — a stricter prompt
  can accidentally suppress this signal.
