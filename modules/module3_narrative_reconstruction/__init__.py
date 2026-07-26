"""
Module 3 — Narrative Reconstruction Engine

Public API:

    from modules.module3_narrative_reconstruction import (
        NarrativeReconstructionEngine,
        ReconstructionInput,
        SessionMeta, ReconstructionConfig, RippleContext,
        NarrativeOutput,
    )

The Dream Graph types (DreamGraph, Node, Edge, NodeType, EdgeType) are re-exported
here for convenience, but their canonical home is modules.module2_dream_graph.models.
Modules 4/5/6 should import the engine and graph types from their respective modules;
do NOT rely on this file as the single source for graph types.

See README.md for the full input/output contract and how Modules 4/5/6 reuse this
engine.
"""

from .engine import NarrativeReconstructionEngine
from .llm_client import NarrativeLLMClient, LLMCallError
from .schemas import (
    # Graph types — canonical home is module2_dream_graph.models; re-exported here
    # so existing callers of this package don't need to change their import paths.
    DreamGraph,
    Node,
    Edge,
    NodeType,
    EdgeType,
    # Module 3-specific input/output types
    ConversationTurn,
    SessionMeta,
    ReconstructionConfig,
    RippleContext,
    ReconstructionInput,
    NarrativeOutput,
    NarrativeBeat,
    GapFill,
    GraphUpdate,
    GenerationMetadata,
)

__all__ = [
    # Engine
    "NarrativeReconstructionEngine",
    "NarrativeLLMClient",
    "LLMCallError",
    # Graph types (from Module 2, re-exported for convenience)
    "DreamGraph",
    "Node",
    "Edge",
    "NodeType",
    "EdgeType",
    # I/O types
    "ConversationTurn",
    "SessionMeta",
    "ReconstructionConfig",
    "RippleContext",
    "ReconstructionInput",
    "NarrativeOutput",
    "NarrativeBeat",
    "GapFill",
    "GraphUpdate",
    "GenerationMetadata",
]
