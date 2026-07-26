"""
Module 3 — Narrative Reconstruction Engine
config.py

Centralized knobs. If you need to swap models, change temperature, or resize the
context window, do it here — nothing else in the module should hardcode these values.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    DRAFT_MODEL: str = "gpt-5.4-mini"   # cheap — use for dev/testing/iteration
    FINAL_MODEL: str = "gpt-5.4"        # quality tier — use for demo/final runs
    TEMPERATURE_DRAFT: float = 0.9
    TEMPERATURE_FINAL: float = 0.85
    MAX_OUTPUT_TOKENS: int = 4000
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: float = 2.0


@dataclass(frozen=True)
class ContextConfig:
    # RAG-style memory: only the last N conversation turns are fed to the LLM,
    # never the full transcript (per the system architecture doc, §3 Module 3 note).
    MAX_CONTEXT_TURNS: int = 6
    # Safety cap so a large Dream Graph doesn't blow up the prompt/context window.
    MAX_GRAPH_NODES_PER_TYPE: int = 25


DEFAULT_MODELS = ModelConfig()
DEFAULT_CONTEXT = ContextConfig()
