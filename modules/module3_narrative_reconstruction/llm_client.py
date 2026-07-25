"""
Module 3 — Narrative Reconstruction Engine
llm_client.py

Thin wrapper around the OpenAI call. Isolated in its own file so:
  - swapping SDKs/providers later touches one file, not the whole engine
  - `mock_mode` lets every other file in this module (and Modules 4/5/6 that call
    this engine) be developed and unit tested with zero API spend
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from .prompts import NARRATIVE_OUTPUT_SCHEMA


class LLMCallError(RuntimeError):
    pass


class NarrativeLLMClient:
    def __init__(self, mock_mode: Optional[bool] = None, api_key: Optional[str] = None):
        # Auto-fallback to mock mode if no key is configured, so the module never
        # hard-crashes just because you haven't wired up billing yet.
        key = api_key or os.environ.get("OPENAI_API_KEY")
        self.mock_mode = mock_mode if mock_mode is not None else (key is None)
        self._api_key = key
        self._client = None
        if not self.mock_mode:
            from openai import OpenAI  # imported lazily so mock mode has no hard dep
            self._client = OpenAI(api_key=self._api_key)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ) -> dict:
        """Returns (parsed_json_dict, usage_dict, latency_seconds)."""
        if self.mock_mode:
            return self._mock_response(user_prompt)

        last_error = None
        for attempt in range(max_retries):
            start = time.time()
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": NARRATIVE_OUTPUT_SCHEMA,
                    },
                )
                latency = time.time() - start
                raw_text = response.choices[0].message.content
                parsed = json.loads(raw_text)
                usage = {
                    "input_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "output_tokens": getattr(response.usage, "completion_tokens", 0),
                }
                return {
                    "parsed": parsed,
                    "usage": usage,
                    "latency_seconds": latency,
                    "raw_text": raw_text,
                }
            except Exception as exc:  # noqa: BLE001 - deliberately broad, we retry generically
                last_error = exc
                if attempt < max_retries - 1:
                    time.sleep(retry_backoff * (attempt + 1))
        raise LLMCallError(f"LLM call failed after {max_retries} attempts: {last_error}")

    # ------------------------------------------------------------------
    def _mock_response(self, user_prompt: str) -> dict:
        """Deterministic canned output so downstream code is testable offline."""
        try:
            payload = json.loads(user_prompt)
        except Exception:
            payload = {}
        graph_nodes = payload.get("dream_graph", {}).get("nodes_by_type", {})
        characters = [n["id"] for n in graph_nodes.get("character", [])] or ["char_unknown"]
        location = (graph_nodes.get("location", [{}])[0] or {}).get("id")

        mock = {
            "beats": [
                {
                    "order": 1,
                    "location_ref": location,
                    "characters_present": characters[:1],
                    "narrative_text": (
                        "[MOCK] The dream opens where the graph left off; details the "
                        "user never mentioned are filled in gently and flagged below."
                    ),
                    "dream_logic_elements": ["the room's walls breathe slightly"],
                    "emotional_tone": "uneasy calm",
                    "gap_fills": [
                        {
                            "original_gap_description": "no stated light source",
                            "fill_content": "a low amber glow with no visible origin",
                            "confidence": 0.4,
                        }
                    ],
                },
                {
                    "order": 2,
                    "location_ref": location,
                    "characters_present": characters,
                    "narrative_text": "[MOCK] A second beat continuing the reconstructed scene.",
                    "dream_logic_elements": [],
                    "emotional_tone": "tense",
                    "gap_fills": [],
                },
            ],
            "implied_new_entities": [],
        }
        return {
            "parsed": mock,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "latency_seconds": 0.0,
            "raw_text": json.dumps(mock),
        }
