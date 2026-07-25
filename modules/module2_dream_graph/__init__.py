"""
module2_dream_graph — Dream Graph. Public entry point.

This is the public entry point for Module 2:

    from modules.module2_dream_graph import build_and_persist_graph

    graph = await build_and_persist_graph(
        dream_id=dream_id,
        user_id=user_id,
        story=story,
    )
"""

from shared.models import Story
from .builder import build_graph
from .db import init_db, load_graph, persist_graph
from .models import DreamGraph, Edge, EdgeType, Node, NodeType
from .totems import link_recurring_symbols


async def build_and_persist_graph(
    dream_id: str,
    user_id: str,
    story: Story,
    version: int = 1,
) -> DreamGraph:
    """The main entrypoint. Builds the typed graph, persists it, then links
    recurring totems and backfills the match results.

    Order matters here: link_recurring_symbols() calls store_node_embedding()
    per node, which does an UPDATE against rows that persist_graph() writes —
    it silently no-ops if those rows don't exist yet. persist_graph() must run
    first so there's something to update.
    """
    graph = await build_graph(dream_id, user_id, story, version)
    await persist_graph(graph)
    graph = await link_recurring_symbols(graph)
    return graph


__all__ = [
    "build_and_persist_graph",
    "build_graph",
    "load_graph",
    "persist_graph",
    "init_db",
    "link_recurring_symbols",
    "DreamGraph",
    "Node",
    "Edge",
    "NodeType",
    "EdgeType",
]
