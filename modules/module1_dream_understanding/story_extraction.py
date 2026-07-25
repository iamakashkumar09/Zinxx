"""Module 1 — Dream Understanding & Conversational Recovery.

Also covers Architecture.md Modules 3 (Narrative Reconstruction),
and 7 (Screenplay Conversion) collapsed into a single Groq call: raw dream/memory text in,
a fully structured Story (title, characters, scenes, lines, sound cues) out. No conversational
follow-up loop and no persistent Dream Graph in this build — everything happens in one pass.

Uses Groq (Llama 3.3 70B) instead of OpenAI, with JSON mode + a normalization pass since
Llama is looser about exact field names than larger models.
"""

import json
import re

from shared.config import GROQ_MODEL
from shared.llm_client import get_client
from shared.models import Story

PROMPT_TEMPLATE = """You are adapting a real dream or memory, described informally by a user, into a short
cinematic audio drama script. The input may be non-linear, vague, or fragmented — that is
expected, since dreams are described that way.

Given the user's raw description below, produce a structured JSON story with:
- title: a short evocative title
- characters: every character mentioned or clearly implied, with an id, name, and role
- scenes: 2-4 scenes forming a clear emotional arc (e.g. calm → rising tension → climax →
  resolution), each with a setting, an emotional_tone, 2-5 dialogue/narration lines
  attributed to a character, and sound_cues (ambient + one-shot) implied by the setting
  or action.

Keep dialogue natural and short — this will be read aloud. Do not invent excessive new
plot; stay close to what the user described, filling gaps only enough to make it coherent
and performable.

Every line's "speaker" must be the id of a character listed in "characters".
Every sound_cue "type" must be either "ambient" or "one-shot". For "one-shot" cues, include
a short "position" hint like "before line 1" or "after line 2" referring to that scene's lines.

You MUST use exactly these field names — do not rename, abbreviate, or omit any of them:

{{
  "title": "string",
  "characters": [{{"id": "string", "name": "string", "role": "string"}}],
  "scenes": [
    {{
      "id": 1,
      "setting": "string",
      "emotional_tone": "string",
      "lines": [{{"speaker": "character_id", "text": "string"}}],
      "sound_cues": [
        {{"type": "ambient", "prompt": "string"}},
        {{"type": "one-shot", "prompt": "string", "position": "before line 1"}}
      ]
    }}
  ]
}}

"id" on each scene is a required integer starting at 1, incrementing per scene. Every
sound_cue's effect description MUST be in a field literally named "prompt" (not "cue",
"description", or anything else).

User's description:
\"\"\"
{raw_input}
\"\"\"

Return only valid JSON matching the schema above. Do not include markdown code fences or any
commentary — the entire response must be a single JSON object.
"""

_CUE_PROMPT_ALIASES = ("prompt", "cue", "description", "sound", "sfx", "effect")


def _normalize(data: dict) -> dict:
    """Tolerate common field-naming drift from smaller/faster models (e.g. Llama via Groq)."""
    for i, scene in enumerate(data.get("scenes") or [], start=1):
        if not isinstance(scene, dict):
            continue
        scene.setdefault("id", i)
        for cue in scene.get("sound_cues") or []:
            if not isinstance(cue, dict) or cue.get("prompt"):
                continue
            for alias in _CUE_PROMPT_ALIASES:
                if cue.get(alias):
                    cue["prompt"] = cue[alias]
                    break
    return data


def _extract_json(raw: str) -> dict:
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model output: {raw[:200]!r}")
    return json.loads(text[start : end + 1])


def _call_llm(raw_input: str) -> str:
    client = get_client()
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=4096,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(raw_input=raw_input)}],
    )
    return completion.choices[0].message.content or ""


def extract_story(raw_input: str) -> Story:
    if not raw_input or not raw_input.strip():
        raise ValueError("Dream/memory description is empty.")

    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            response_text = _call_llm(raw_input)
            data = _extract_json(response_text)
            data = _normalize(data)
            return Story.model_validate(data)
        except Exception as exc:  # noqa: BLE001 - retry once on any parse/validation failure
            last_error = exc
    raise RuntimeError(f"Story extraction failed after retry: {last_error}") from last_error
