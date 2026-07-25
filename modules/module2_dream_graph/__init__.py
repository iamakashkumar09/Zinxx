"""
module2_dream_graph — Dream Graph. Public entry point.

Exports are split into two tiers so callers that only need the data shapes
(e.g. Module 3's schemas.py) can import without triggering the Postgres /
pgvector / OpenAI dependency chain:

  TIER 1 — pure schema types (no external deps, always safe to import):
      DreamGraph, Node, Edge, NodeType, EdgeType

  TIER 2 — persistence + embedding (requires pgvector, openai, asyncpg):
      build_and_persist_graph, build_graph, load_graph, persist_graph,
      init_db, link_recurring_symbols

Usage — schema-only (Module 3, Module 4, Module 6, tests):
    from modules.module2_dream_graph import DreamGraph, Node, NodeType

Usage — full pipeline (app.py, Module 5):
    from modules.module2_dream_graph import build_and_persist_graph
"""

# Tier 1: pure models — no heavy deps, safe for any importer
from .models import DreamGraph, Edge, EdgeType, Node, NodeType


def _load_persistence():
    """Lazy import guard so the module can be imported in environments
    without pgvector/asyncpg installed (e.g. CI, unit tests, Module 3 schema checks)."""
    from .builder import build_graph
    from .db import init_db, load_graph, persist_graph
    from .totems import link_recurring_symbols
    return build_graph, init_db, load_graph, persist_graph, link_recurring_symbols


async def init_db() -> None:
    """Initialize the Postgres database and create tables if they don't exist.
    Lazy-loads the db module on first call."""
    _, _init_db, _, _, _ = _load_persistence()
    await _init_db()


async def build_and_persist_graph(
    dream_id: str,
    user_id: str,
    story,  # shared.models.Story — typed loosely to avoid circular import at module load
    version: int = 1,
) -> DreamGraph:
    """The main entrypoint. Builds the typed graph, links recurring
    totems, persists everything, and returns the finished graph.

    Heavy imports (pgvector, openai, asyncpg) are deferred to first call.
    """
    build_graph, init_db, load_graph, persist_graph, link_recurring_symbols = _load_persistence()
    graph = await build_graph(dream_id, user_id, story, version)
    graph = await link_recurring_symbols(graph)
    await persist_graph(graph)
    return graph


__all__ = [
    # Tier 1 — always available
    "DreamGraph",
    "Node",
    "Edge",
    "NodeType",
    "EdgeType",
    # Tier 2 — available after first call (lazy-loaded)
    "build_and_persist_graph",
    "init_db",
]
