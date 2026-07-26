"""Module 7 — Screenplay Conversion.

Turns Module 3's reconstructed narrative (prose beats) into the structured Story schema
(shared/models.py) that Modules 8-10 already consume — the same contract Module 1's
story_extraction.py produces directly, but now built from the *reconstructed* narrative
(gap-filled, dream-logic-preserving) instead of the raw first-pass extraction.

Character/location facts are pulled mechanically from Module 2's DreamGraph (it's the
source of truth — no reason to ask an LLM to re-derive a character's name when the graph
already has it). The one thing that genuinely needs an LLM, per Architecture.md's own
framing of this module, is turning each beat's narrative *prose* into actual dialogue/
narration lines plus ambient/one-shot sound cues — that's a generative task.
"""

import json
import re

from shared.config import OPENAI_MODEL
from shared.models import Character, Line, Scene, SoundCue, Story
from shared.openai_client import get_client

from modules.module2_dream_graph.models import DreamGraph, NodeType
from modules.module3_narrative_reconstruction.schemas import NarrativeOutput

PROMPT_TEMPLATE = """You are a screenwriter converting a reconstructed dream narrative into an audio
drama script. Below is the narrative broken into ordered beats, plus the cast of characters
involved. Each beat is prose describing what happens — your job is to turn each beat into
actual spoken lines (dialogue or first-person narration) and implied sound cues.

Cast:
{characters_json}

Beats (in order):
{beats_json}

For each beat, produce:
- "lines": 0-4 short spoken lines, each attributed to a character id from the cast above
  (use the narrator/first-person character for internal narration). Keep lines natural and
  short — this will be read aloud by a TTS voice. Stay faithful to the beat's narrative_text;
  don't invent plot beyond what's described.
  * A line's "text" must be ONLY the actual words spoken or narrated aloud — real, quotable
    speech. NEVER put a stage direction, action description, or parenthetical like
    "(silent, watching)" or "(a low growl)" into "text" — a TTS voice will read it verbatim
    and it will sound broken. If a character in this beat doesn't actually speak or narrate
    (an animal, a crowd, a silent presence), give them NO line at all — express what they're
    doing through a sound_cue instead (e.g. a low growl, footsteps, murmuring voices), not a
    fake quote.
  * It is fine, and occasionally correct, for a beat to have zero lines when nothing is
    actually said — but this must be the exception, not the rule. This is an audio drama:
    most beats need SOME first-person narration from the narrator/dreamer character
    describing what's happening, even if no other character speaks. Do not leave every
    beat silent just because no one else in the scene talks — the dreamer is always there
    and can always narrate.
- "sound_cues": ambient + one-shot sound effects implied by the beat's setting or action. Be
  thorough and literal here — pull out every concrete sound event actually described or implied
  in the beat's narrative_text (thunder, rain, an animal's cry, footsteps, a door, glass, a
  bell, a crowd's murmur, fire crackling, etc.), not just a generic ambience bed for the
  setting. This is the primary channel for anything non-human or non-verbal in the scene.
  Every "one-shot" cue needs a short "position" hint like "before line 1" or "after line 2".

Return only valid JSON of the form:
{{
  "title": "a short evocative title for the whole piece",
  "beats": [
    {{
      "beat_order": 1,
      "lines": [{{"speaker": "character_id", "text": "string"}}],
      "sound_cues": [
        {{"type": "ambient", "prompt": "string"}},
        {{"type": "one-shot", "prompt": "string", "position": "before line 1"}}
      ]
    }}
  ]
}}

Every sound_cue's effect description MUST be in a field literally named "prompt". Do not
include markdown fences or commentary — the entire response must be a single JSON object.
"""


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


_CUE_PROMPT_ALIASES = ("prompt", "cue", "description", "sound", "sfx", "effect")

_KEYWORD_RE = re.compile(r"[a-zA-Z]{4,}")
_STOPWORDS = {"with", "from", "that", "this", "then", "them", "into", "onto", "over", "near", "some"}


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in _KEYWORD_RE.findall(text)} - _STOPWORDS


def _ensure_sound_coverage(scenes: list[Scene], graph: DreamGraph) -> None:
    """Belt-and-suspenders pass: narrative reconstruction is generative and can drop a
    concrete sound event even when explicitly instructed to preserve it (confirmed by
    testing — the same source dream sometimes keeps every sound, sometimes drops several).
    This mechanically checks every sound Module 1 originally captured against what actually
    made it into the final sound_cues, and backfills anything missing as an ambient cue on
    the scene sharing that event's original setting, so nothing is silently lost."""
    all_cue_keywords = [_keywords(cue.prompt) for scene in scenes for cue in scene.sound_cues]

    for event in graph.nodes_by_type(NodeType.event):
        sources = [s.strip() for s in event.attributes.get("sound_sources", "").split(";") if s.strip()]
        if not sources:
            continue
        location = event.attributes.get("location", "")
        candidates = [s for s in scenes if s.setting == location] or scenes
        for source in sources:
            source_kw = _keywords(source)
            if not source_kw:
                continue
            if any(source_kw & existing for existing in all_cue_keywords):
                continue
            target = candidates[0]
            target.sound_cues.append(SoundCue(type="ambient", prompt=source))
            all_cue_keywords.append(source_kw)


def _fallback_narrator_id(characters: list[Character]) -> str | None:
    for c in characters:
        if c.id == "narrator" or "narrat" in c.role.lower() or "dreamer" in c.role.lower():
            return c.id
    return characters[0].id if characters else None


def _ensure_narration(scenes: list[Scene], beats, narrator_id: str | None) -> None:
    """Guards against the LLM giving every beat zero lines — confirmed to happen in testing,
    and previously a hard pipeline failure ("no dialogue lines in any scene") with no
    fallback, since allowing individual lineless beats (for non-speaking presences) opened
    the door to the LLM leaving the WHOLE story silent. If that happens, fall back to a
    short first-person narration line per scene straight from the beat's own prose — the
    user always gets a playable result instead of an outright error."""
    if any(s.lines for s in scenes) or not narrator_id:
        return
    for scene, beat in zip(scenes, beats):
        text = beat.narrative_text.strip()
        if len(text) > 200:
            text = text[:197].rsplit(" ", 1)[0] + "..."
        if text:
            scene.lines.append(Line(speaker=narrator_id, text=text))


def _normalize_cue(cue: dict) -> dict:
    if not cue.get("prompt"):
        for alias in _CUE_PROMPT_ALIASES:
            if cue.get(alias):
                cue["prompt"] = cue[alias]
                break
    return cue


def _call_llm(characters_payload: list[dict], beats_payload: list[dict]) -> dict:
    client = get_client()
    prompt = PROMPT_TEMPLATE.format(
        characters_json=json.dumps(characters_payload, ensure_ascii=False, indent=2),
        beats_json=json.dumps(beats_payload, ensure_ascii=False, indent=2),
    )
    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_completion_tokens=4096,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(completion.choices[0].message.content or "")


def convert_to_screenplay(
    narrative: NarrativeOutput, graph: DreamGraph, title_hint: str | None = None
) -> Story:
    """The Module 7 entrypoint. Story.characters comes straight from the graph (authoritative);
    Story.scenes come from a 1:1 mapping of narrative beats, with the LLM only supplying the
    lines/sound_cues for each beat — everything else (setting, emotional_tone) is resolved
    from the graph/beat directly, not re-generated.
    """
    character_nodes = graph.nodes_by_type(NodeType.character)
    characters = [
        Character(id=n.id, name=n.label, role=n.attributes.get("role", "")) for n in character_nodes
    ]
    valid_character_ids = {c.id for c in characters}

    if not narrative.beats:
        raise ValueError("Narrative has no beats to convert into a screenplay.")

    characters_payload = [{"id": c.id, "name": c.name, "role": c.role} for c in characters]
    beats_payload = [
        {
            "beat_order": b.order,
            "narrative_text": b.narrative_text,
            "emotional_tone": b.emotional_tone,
            "characters_present": b.characters_present,
            "setting": (graph.node(b.location_ref).label if b.location_ref and graph.node(b.location_ref) else None),
        }
        for b in narrative.beats
    ]

    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            data = _call_llm(characters_payload, beats_payload)
            beats_by_order = {b["beat_order"]: b for b in data.get("beats", [])}

            scenes: list[Scene] = []
            for beat in narrative.beats:
                llm_beat = beats_by_order.get(beat.order, {})
                setting = graph.node(beat.location_ref).label if beat.location_ref and graph.node(beat.location_ref) else "an unplaced dream setting"

                lines: list[Line] = []
                for raw_line in llm_beat.get("lines", []):
                    speaker = raw_line.get("speaker")
                    text = raw_line.get("text")
                    if not text:
                        continue
                    if speaker not in valid_character_ids:
                        speaker = beat.characters_present[0] if beat.characters_present else (characters[0].id if characters else "narrator")
                    lines.append(Line(speaker=speaker, text=text))

                sound_cues = [
                    SoundCue(**_normalize_cue(dict(cue)))
                    for cue in llm_beat.get("sound_cues", [])
                    if _normalize_cue(dict(cue)).get("prompt")
                ]

                scenes.append(
                    Scene(
                        id=beat.order,
                        setting=setting,
                        emotional_tone=beat.emotional_tone or "neutral",
                        lines=lines,
                        sound_cues=sound_cues,
                    )
                )

            _ensure_narration(scenes, narrative.beats, _fallback_narrator_id(characters))

            if not any(s.lines for s in scenes):
                raise ValueError("Screenplay conversion produced no dialogue lines in any scene.")

            _ensure_sound_coverage(scenes, graph)

            return Story(
                title=data.get("title") or title_hint or "Untitled Dream",
                characters=characters,
                scenes=scenes,
            )
        except Exception as exc:  # noqa: BLE001 - retry once on any parse/validation failure
            last_error = exc

    raise RuntimeError(f"Screenplay conversion failed after retry: {last_error}") from last_error
