"""Module 11 — Quality/Consistency Review.

Job (per Architecture.md): catch a character whose voice/emotion contradicts earlier
scenes, or a line implying an action/sound with no corresponding SFX cue — before final
render. One OpenAI pass over the finished screenplay + generated-audio metadata
(durations, cue list); text-only reasoning, nearly free relative to audio generation cost.

Advisory, not a gate — this module's caller (app.py) must never let a QA failure or a
found issue block Module 10 from rendering. A hackathon demo should never fail to produce
audio because a review pass found something to nitpick.
"""

import json
import re

from shared.config import OPENAI_MODEL
from shared.models import Story
from shared.openai_client import get_client

from modules.module11_qa_consistency.schemas import QAIssue, QAReport

PROMPT_TEMPLATE = """You are a continuity and quality reviewer for an audio drama production,
checking a finished screenplay plus its generated-audio metadata before final render.

Screenplay (scenes, dialogue, performance direction, emotion scores, line durations, and
sound cues already generated):
{story_json}

Check for exactly two kinds of issues:
1. VOICE/EMOTION CONTRADICTIONS: a line's performance_direction or emotion_scores that
   don't make sense given the surrounding narrative context, or a character's emotional
   delivery that contradicts how they were performing in an earlier scene with no
   narrative reason for the shift.
2. MISSING SFX: dialogue or narration that clearly implies a physical action or sound (a
   door opening, footsteps, something breaking, weather, etc.) with no corresponding entry
   in that scene's sound_cues list.

Only report genuine issues — do not invent nitpicks. Most well-generated scenes will have
zero issues; an empty issues list is a good and expected outcome, not a failure to find
something.

Return only valid JSON of the form:
{{
  "consistency_score": 0-100,
  "issues": [
    {{
      "scene_id": 1,
      "line_index": 2,
      "category": "voice_emotion_contradiction",
      "severity": "low",
      "description": "string"
    }}
  ]
}}

"line_index" may be null for scene-level issues (like missing SFX) — omit it or set null
rather than guessing a line. "category" must be either "voice_emotion_contradiction" or
"missing_sfx". Do not include markdown fences or commentary — the entire response must be
a single JSON object.
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


def _build_payload(story: Story) -> dict:
    return {
        "title": story.title,
        "characters": [{"id": c.id, "name": c.name, "role": c.role} for c in story.characters],
        "scenes": [
            {
                "id": s.id,
                "setting": s.setting,
                "emotional_tone": s.emotional_tone,
                "lines": [
                    {
                        "index": i,
                        "speaker": line.speaker,
                        "text": line.text,
                        "emotion_scores": line.emotion_scores,
                        "performance_direction": line.performance_direction,
                        "duration_ms": line.duration_ms,
                    }
                    for i, line in enumerate(s.lines)
                ],
                "sound_cues": [
                    {
                        "type": cue.type,
                        "prompt": cue.prompt,
                        "position": cue.position,
                        "position_ms": cue.position_ms,
                    }
                    for cue in s.sound_cues
                ],
            }
            for s in story.scenes
        ],
    }


def review_story(story: Story) -> QAReport:
    client = get_client()
    payload = _build_payload(story)
    prompt = PROMPT_TEMPLATE.format(story_json=json.dumps(payload, ensure_ascii=False, indent=2))

    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            completion = client.chat.completions.create(
                model=OPENAI_MODEL,
                max_completion_tokens=2048,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            data = _extract_json(completion.choices[0].message.content or "")

            issues = [
                QAIssue(
                    scene_id=int(item.get("scene_id", 0)),
                    line_index=item.get("line_index"),
                    category=item.get("category", "other"),
                    severity=item.get("severity", "low"),
                    description=item.get("description", ""),
                )
                for item in data.get("issues", [])
            ]
            score = max(0, min(100, int(data.get("consistency_score", 100))))
            return QAReport(issues=issues, consistency_score=score, model=OPENAI_MODEL)
        except Exception as exc:  # noqa: BLE001 - retry once on any parse/validation failure
            last_error = exc

    raise RuntimeError(f"Module 11 QA review failed after retry: {last_error}") from last_error
