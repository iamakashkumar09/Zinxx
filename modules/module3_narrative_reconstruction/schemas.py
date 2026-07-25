"""
Module 3 — Narrative Reconstruction Engine
schemas.py

Pure data shapes. No logic lives here on purpose — if the contract with Modules
2/4/5/6/7 ever breaks, this is the first (and hopefully only) file you need to read.

DreamGraph, Node, Edge, NodeType, EdgeType are the canonical types from Module 2.
Module 3 never re-defines them — it only imports and reads them.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, Literal
import time
import uuid

# ---------------------------------------------------------------------------
# Re-export Module 2's canonical Dream Graph types.
# Module 3 is a READ-ONLY consumer of the graph — it never writes to it.
# All downstream code in this module (prompts, postprocess, engine) should use
# these names, not the old DreamGraphNode/DreamGraphEdge aliases.
# ---------------------------------------------------------------------------
from modules.module2_dream_graph.models import (  # noqa: F401  (re-exported)
    DreamGraph,
    Node,
    Edge,
    NodeType,
    EdgeType,
)


# ---------------------------------------------------------------------------
# Input: trimmed conversation context (Modules 1/2 conversational recovery)
# ---------------------------------------------------------------------------

@dataclass
class ConversationTurn:
    role: Literal["user", "assistant"]
    text: str
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Input: session + config
# ---------------------------------------------------------------------------

@dataclass
class SessionMeta:
    dream_id: str
    user_id: str
    session_id: str
    language: str = "en"
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReconstructionConfig:
    model_tier: Literal["draft", "final"] = "draft"
    preserve_dream_logic: bool = True
    target_length: Literal["short", "medium", "long"] = "medium"
    # Injected by Module 4 (layer) or Module 6 (lens) callers. Module 3 treats these
    # as opaque persona strings — it has no opinion on what a "layer" or "lens" is.
    layer_persona: Optional[str] = None
    lens_persona: Optional[str] = None
    debug: bool = False


@dataclass
class RippleContext:
    """Set only when Module 5 is asking for a partial regeneration after a graph edit."""
    previous_output: "NarrativeOutput"
    changed_node_ids: list[str] = field(default_factory=list)


@dataclass
class ReconstructionInput:
    # Module 2's DreamGraph — the single source of truth for the graph structure.
    dream_graph: DreamGraph
    session_meta: SessionMeta
    conversation_context: list[ConversationTurn] = field(default_factory=list)
    config: ReconstructionConfig = field(default_factory=ReconstructionConfig)
    ripple: Optional[RippleContext] = None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@dataclass
class GapFill:
    gap_id: str
    original_gap_description: str
    fill_content: str
    confidence: float  # 0.0-1.0, LLM self-reported
    source: Literal["inferred", "user_stated"] = "inferred"


@dataclass
class NarrativeBeat:
    beat_id: str
    order: int
    location_ref: Optional[str]           # Node.id (location node)
    characters_present: list[str]         # Node.id list (character nodes)
    narrative_text: str
    dream_logic_elements: list[str] = field(default_factory=list)
    gap_fills: list[GapFill] = field(default_factory=list)
    emotional_tone: Optional[str] = None


@dataclass
class GraphUpdate:
    """A new node/edge the LLM implied that doesn't yet exist in the Dream Graph.
    Handed back to Module 2 to merge — Module 3 never writes to the graph itself."""
    kind: Literal["node", "edge"]
    payload: dict


@dataclass
class GenerationMetadata:
    model: str
    temperature: float
    input_tokens: int = 0
    output_tokens: int = 0
    latency_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    debug: Optional[dict] = None  # raw prompt/response, only populated if config.debug


@dataclass
class NarrativeOutput:
    narrative_id: str
    beats: list[NarrativeBeat]
    graph_updates: list[GraphUpdate] = field(default_factory=list)
    provenance_map: dict = field(default_factory=dict)   # beat_id -> [node_ids]
    warnings: list[str] = field(default_factory=list)
    generation_metadata: Optional[GenerationMetadata] = None

    def to_dict(self) -> dict:
        return asdict(self)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
