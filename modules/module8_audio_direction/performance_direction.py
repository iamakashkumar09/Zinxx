"""Part of Module 8 — Audio Direction Engine.

Generates a vocal performance instruction for each line, batched per scene, using the
line text + emotion_scoring.py's output as signal. This is the "how should it sound"
planning step that feeds directly into Module 9's (audio_production) TTS instructions.

Uses OpenAI (same OPENAI_MODEL as Module 1) — Architecture.md notes a cheaper/faster model
is "plenty" for this planning-over-structured-data task, but this build keeps it on the
same model as extraction for simplicity; tune OPENAI_MODEL down here independently later
if you want to save cost once quality is confirmed good enough.
"""

import json
import re

from shared.config import OPENAI_MODEL
from shared.models import Story
from shared.openai_client import get_client

PROMPT_TEMPLATE = """You are a voice director for an audio drama. Below is one scene from the
story "{title}", with its setting, emotional tone, and each line's text plus its emotion
classifier scores (from a text-emotion model — treat these as a rough signal, not ground truth).

Scene setting: {setting}
Scene emotional tone: {emotional_tone}

Lines (JSON array, in order):
{lines_json}

For each line, in the same order, write one short vocal performance direction (one sentence)
describing HOW it should be voiced: pacing, breath, tone, volume, emotional trajectory within
the line. Be specific and performable by a voice actor or TTS engine, e.g. "Breathless and
uncertain, voice tightening slightly with each word."

Return only a valid JSON object of the form {{"directions": ["...", "..."]}} with exactly one
string per input line, in the same order as the input lines. No markdown fences, no commentary.
"""


def _extract_json_array(raw: str) -> list:
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model output: {raw[:200]!r}")
    data = json.loads(text[start : end + 1])
    directions = data.get("directions")
    if not isinstance(directions, list):
        raise ValueError(f"Expected a 'directions' array in model output: {data!r}")
    return directions


def _directions_for_scene(title: str, scene) -> list[str]:
    lines_payload = [
        {"speaker": line.speaker, "text": line.text, "emotion_scores": line.emotion_scores}
        for line in scene.lines
    ]
    prompt = PROMPT_TEMPLATE.format(
        title=title,
        setting=scene.setting,
        emotional_tone=scene.emotional_tone,
        lines_json=json.dumps(lines_payload, ensure_ascii=False, indent=2),
    )
    client = get_client()

    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            completion = client.chat.completions.create(
                model=OPENAI_MODEL,
                max_completion_tokens=2048,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = completion.choices[0].message.content or ""
            directions = _extract_json_array(response_text)
            if len(directions) != len(scene.lines):
                raise ValueError(
                    f"Expected {len(scene.lines)} directions, got {len(directions)}"
                )
            return [str(d) for d in directions]
        except Exception as exc:  # noqa: BLE001 - retry once
            last_error = exc
    raise RuntimeError(f"Performance direction failed for scene {scene.id}: {last_error}") from last_error


def direct_story(story: Story) -> Story:
    for scene in story.scenes:
        if not scene.lines:
            continue
        directions = _directions_for_scene(story.title, scene)
        for line, direction in zip(scene.lines, directions):
            line.performance_direction = direction
    return story
